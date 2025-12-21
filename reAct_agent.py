from typing import Annotated, TypedDict, List
import os
import textwrap
import operator
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AnyMessage, trim_messages
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
    # 'add_messages' ensures new messages are appended to history
    messages: Annotated[List[AnyMessage], add_messages]
    loop_step: Annotated[int, operator.add]

# ==============================================================================
# INITIALIZE MODEL & NODES
# ==============================================================================

def navigation_router(state: AgentState):
    """
    The router that decides whether to go to tools or end the workflow.
    If the last message contains tool_calls, we go to the tools node.
    Otherwise, we end the workflow.
    """
    current_step = state.get("loop_step", 0)
    if current_step >= 10:
        return END
    
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    else:
        return END

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

    def agent_node(state: AgentState):
        """
        The main reasoning node.
        It receives the history and decides whether to answer or call a tool.
        """

        system_msg = textwrap.dedent("""
            You are an expert C/C++ Engineer analyzing the GNU Coreutils library.
            Your task is to assist with questions about GNU Coreutils asked by the user.
            To understand high-level behavior or 'Why', use 'search_concepts'.
            To see C code, structs, or functions, use 'search_implementations'.
            RULES FOR EFFICIENCY:
            1. **DO NOT** output internal monologue, plans, or 'I will now...' statements.
            2. If you need information, generate the Tool Call **immediately**.
            3. If you have enough information, output the final answer **immediately**.
            4. Do not double-check your work. Be decisive.
            5. Keep your responses concise and to the point and make sure the response is human understandable.
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

        # We prepend the system message to the history for the model call
        # (Note: We don't add it to state['messages'] to avoid duplicating it in history)
        messages = [system_msg] + trimmed_messages

        response = llm_with_tools.invoke(messages)
        return {"messages": [response], "loop_step": 1}

    # The Prebuilt ToolNode handles execution of the Python functions above
    tool_node = ToolNode(tools,)

    memory = InMemorySaver()
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set Entry Point
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    # Add Conditional Edge (The ReAct Router)
    workflow.add_conditional_edges(
        "agent",                # The node that just finished
        navigation_router,      # The function that decides what's next
        {                       # The Map: {Router Output : Graph Node Name}
            "tools": "tools",
            END: END
        }
    )

    # Add Edge from Tools back to Agent (The Loop)
    workflow.add_edge("tools", "agent")

    # Compile
    return workflow.compile(checkpointer=memory)


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
                    msg = event["agent"]["messages"][0]
                    if msg.tool_calls:
                        tool_name = msg.tool_calls[0]['name']
                        tool_args = msg.tool_calls[0]['args']
                        # st.markdown(f"🛠️ **Decided to call:** `{tool_name}`")
                        status.update(label=f"Executing {tool_name}...", state="running")
                    else:
                        # If no tool call, this is the final answer
                        final_response = msg.content

                # CASE B: The Tool Just Finished
                elif "tools" in event:
                    msg = event["tools"]["messages"][0]
                    # We truncate tool output in the UI because it can be huge (long C files)
                    # preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    # st.markdown(f"📄 **Tool Output:** {preview}")
                    status.update(label="Processing tool output...", state="running")
            
            # 3. Final Polish
            status.update(label="Your response is ready!", state="complete", expanded=True)

            # Display Final Answer
            st.markdown(final_response)

            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": final_response})

