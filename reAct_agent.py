from typing import Annotated, TypedDict, List
import os
import textwrap
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AnyMessage, trim_messages, AIMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
import streamlit as st
from dotenv import load_dotenv
from utils.tools import search_concepts, search_implementations

load_dotenv()

# Initialize Streamlit
st.set_page_config(page_title="GNU Coreutils AI Navigator", page_icon="🐧")
st.markdown("""
    # 🐧 GNU Coreutils AI Navigator
    
    **Your expert co-pilot for exploring the source code of standard Linux utilities (`ls`, `cp`, `mv`, etc.).**
    
    
    ### 🚀 Key Features
    * **🔍 Conceptual Search:** Can answer detailed answer about library functions.
    * **⚙️ Short Term Memory:** The agent remembers recent interactions to provide contextually relevant answers.
    * **🛠️ Tool Integration:** Leverages specialized tools to fetch code snippets and definitions from the GNU Coreutils codebase.
    * **🤖 ReAct Agent Architecture:** Combines reasoning and tool usage for efficient problem-solving.
            
    ### 💡 Try Asking...
    * *"How does the `cp` command handle symbolic links?"*
    * *"Find the struct definition for `fileinfo` in ls.c"*
""")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Let's start chatting! 👇"}]

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(os.urandom(8).hex())

# ==============================================================================
# DEFINE LANGGRAPH STATE
# ==============================================================================

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    loop_step: int
    terminate: bool
    terminate_message: str

# ==============================================================================
# INITIALIZE MODEL & NODES
# ==============================================================================

def navigation_router(state: AgentState):
    """
    The router that decides whether to go to tools or end the workflow.
    If the last message contains tool_calls, we go to the tools node.
    Otherwise, we end the workflow.
    """
    print("Inside Navigation Router")
    if state.get("terminate", False):
        return END

    current_step = state.get("loop_step", 0)
    print("Current Step:", current_step)
    if current_step >= 5:
        return "finalizer"
    
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        print("Routing to tools...")
        return "tools"
    
    print("Routing to end...")
    return END

def sanitize(messages):
    """
    Docstring for sanitize
    
    :param messages: List[AnyMessage]
    :return: List[AnyMessage]
    """
    cleaned = []
    for m in messages:
        if isinstance(m, ToolMessage):
            continue
        if isinstance(m, AIMessage):
            cleaned.append(AIMessage(content=m.content))
        else:
            cleaned.append(m)
    return cleaned


# ==============================================================================
# BUILD THE GRAPH
# ==============================================================================

@st.cache_resource
def initialize_graph():
    """
    Initializes the Graph AND the MemorySaver once.
    Returns the compiled application.
    """

    # List of tools for the Agent
    tools = [search_concepts, search_implementations]
    # Initialize LLM and bind tools
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.3)
    llm_with_tools = llm.bind_tools(tools)
    final_llm = llm.bind_tools([], tool_choice="none")


    def agent_node(state: AgentState):
        """
        The main reasoning node.
        It receives the history and decides whether to answer or call a tool.
        """
        print("Inside Agent Node")

        system_msg = textwrap.dedent("""
            You are an expert C/C++ technical assistant analyzing the GNU Coreutils library **ONLY**.
            To understand high-level behavior, search for documentation and developer comments, use 'search_concepts'.
            To search for C code, structs, enums or function use 'search_implementations'.
            If the user asks about ANY topic unrelated to Coreutils, C programming, or Linux system calls, you must:
            1. REFUSE to answer.
            2. State clearly: 'I can only assist with GNU Coreutils and related system programming topics.'
            3. DO NOT try to be helpful or provide a 'brief' answer to the off-topic query.
            If you are **UNSURE** or **UNABLE TO ANSWER**, output the final answer **immediately** or specify 'I cannot help you with this query'.
            The user may ask wrong or misleading questions. Always provide the correct information.
            Do not double-check your work. Be decisive.
            Keep your responses concise and to the point and make sure the response is human understandable.
            Always cite the file name when explaining logic.
        """).strip()

        # System prompt to ground the agent's behavior
        system_msg = SystemMessage(content=system_msg)

        trimmed_messages = trim_messages(state["messages"],
                                        strategy="last",
                                        token_counter=count_tokens_approximately,
                                        max_tokens=10000,
                                        start_on="human",
                                        end_on=("human", "tool"),)

        messages = [system_msg] + trimmed_messages

        try:
            response = llm_with_tools.invoke(messages)
            current_step = -1
            if response.tool_calls:
                current_step = state.get("loop_step", 0)
            return {"messages": [response], "loop_step": current_step + 1, "terminate": False, "terminate_message": ""}
        except Exception as e:
            error_message = e.message
            match = re.search(r"Please try again in (.*?)\.", error_message)
            message = ""
            if match:
                wait_time = match.group(1)
                message = f"⚠️ System is currently busy. Please wait {wait_time} before trying again."
            else:
                message = "⚠️ Rate limit reached. Please try again in a few minutes."
            return {"messages": [], "loop_step": 0, "terminate": True, "terminate_message": message}
        

    def finalizer_node(state: AgentState):
        """
        Forces the agent to generate a final answer using currently available info.
        """

        print("Inside Finalizer Node")

        # Sanitize messages to remove tool call metadata
        sanitized_messages = sanitize(state["messages"])

        # Create a system message that effectively says "Time's up!"
        force_msg = SystemMessage(content=(
            "SYSTEM NOTICE: You have reached the maximum number of reasoning steps. "
            "Stop using tools immediately. "
            "Summarize the information you have gathered so far to answer the user's question. "
            "If you don't have the full answer, explain what you found and what is missing."
        ))
        
        messages = sanitized_messages + [force_msg]

        try:
            response = final_llm.invoke(messages)
            return {"messages": [response], "loop_step": 0, "terminate": False, "terminate_message": ""}
        except Exception as e:
            error_message = e.message
            match = re.search(r"Please try again in (.*?)\.", error_message)
            message = ""
            if match:
                wait_time = match.group(1)
                message = f"⚠️ System is currently busy. Please wait {wait_time} before trying again."
            else:
                message = "⚠️ Rate limit reached. Please try again in a few minutes."
            return {"messages": [], "loop_step": 0, "terminate": True, "terminate_message": message}

    tool_node = ToolNode(tools,)

    memory = InMemorySaver()
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("finalizer", finalizer_node)

    # Set Entry Point
    workflow.add_edge(START, "agent")

    # Add Conditional Edge (The ReAct Router)
    workflow.add_conditional_edges(
        "agent",                
        navigation_router,      
        {                       
            "tools": "tools",
            "finalizer": "finalizer",
            END: END
        }
    )

    # Add Edge from Tools back to Agent (The Loop)
    workflow.add_edge("tools", "agent")
    workflow.add_edge("finalizer", END)

    # Compile
    temp =  workflow.compile(checkpointer=memory)
    return temp

app = initialize_graph()


# Display existing chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

if prompt := st.chat_input("How can I assist you?..."):

    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.status("Agent is working...", expanded=True) as status:

            input_message = HumanMessage(content=prompt)
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            final_response = ""
            
            for event in app.stream({"messages": [input_message]}, config=config):
                # CASE A: The Agent Just Spoke (Thinking or Tool Call)
                if "agent" in event:
                    if event["agent"].get("terminate", False):
                        final_response = event["agent"].get("terminate_message", "⚠️ The agent has terminated the conversation.")
                        break
                    msg = event["agent"]["messages"][0]
                    if msg.tool_calls:
                        tool_name = msg.tool_calls[0]['name']
                        tool_args = msg.tool_calls[0]['args']
                        status.update(label=f"Executing {tool_name}...", state="running")
                    else:
                        # If no tool call, this is the final answer
                        final_response = msg.content

                # CASE B: The Tool Just Finished
                elif "tools" in event:
                    msg = event["tools"]["messages"][0]
                    status.update(label="Processing tool output...", state="running")

                # CASE C: The Finalizer Just Finished
                elif "finalizer" in event:
                    if event["finalizer"].get("terminate", False):
                        final_response = event["finalizer"].get("terminate_message", "⚠️ The agent has terminated the conversation.")
                        break
                    msg = event["finalizer"]["messages"][0]
                    final_response = msg.content

            
            # 3. Final Polish
            status.update(label="Your response is ready!", state="complete", expanded=True)

            # Display Final Answer
            st.markdown(final_response)

            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": final_response})

