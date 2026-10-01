# graph.py
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from router_schema import router_chain
from general_chat_node import general_chat_node
from accounting_subgraph import accounting_subgraph  # builder, compiled nahi
from state import ChatState
from checkpointer import get_checkpointer  #singleton

#  ye function btata h ki chat general h ya amount ki h 
async def router_node(state: ChatState):
    last_message = state["messages"][-1].content
    result = await router_chain.ainvoke({"input": last_message})
    return {"intent": result.intent}
#  ye function call h 

def route_intent(state: ChatState):
    intent = state.get("intent")
    if intent == "accounting":
        return "accounting"
    return "general_chat"

#Graph
graph = StateGraph(ChatState)

graph.add_node("router", router_node)
graph.add_node("general_chat", general_chat_node)
graph.add_node("accounting", accounting_subgraph.compile())  # 0Ek baar compile, node ki tarah

graph.add_edge(START, "router")
graph.add_conditional_edges("router", route_intent, {
    "general_chat": "general_chat",
    "accounting": "accounting"
})
graph.add_edge("general_chat", END)
graph.add_edge("accounting", END)

async def build_app():
    checkpointer = await get_checkpointer()  # ✅ Singleton reuse
    return graph.compile(checkpointer=checkpointer)

# async def main():
#     app = await build_app()
#     result = await app.ainvoke(
#         {"messages": [HumanMessage(content="Kitanu ne 200 ka kaam kiya")]},
#         config={"configurable": {"thread_id": "1"}}
#     )
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(main())