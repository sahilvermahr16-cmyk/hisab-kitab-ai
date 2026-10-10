# graph.py
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from router_schema import router_chain, attendance_safety_net
from general_chat_node import general_chat_node
from accounting_subgraph import accounting_subgraph  # builder, compiled nahi
from report_subgraph import report_subgraph  # builder, compiled nahi
from state import ChatState
from checkpointer import get_checkpointer  #singleton

#  ye function btata h ki chat general h ya amount ki h 
async def router_node(state: ChatState):
    last_message = state["messages"][-1].content
    result = await router_chain.ainvoke({"input": last_message})
    intent = result.intent
    if intent == "general_chat" and attendance_safety_net(last_message):
        print("🔀 ROUTER: haazri ka bayan lagta hai — general_chat ki jagah accounting")
        intent = "accounting"
    if intent == "general_chat":
        from family_rules import money_safety_net
        if money_safety_net(last_message):
            print("🔀 ROUTER: paise ka len-den lagta hai — general_chat ki jagah accounting")
            intent = "accounting"
    return {"intent": intent}
#  ye function call h 

def route_intent(state: ChatState):
    intent = state.get("intent")
    if intent == "accounting":
        return "accounting"
    if intent == "report":
        return "report"
    return "general_chat"

#Graph
graph = StateGraph(ChatState)

graph.add_node("router", router_node)
graph.add_node("general_chat", general_chat_node)
graph.add_node("accounting", accounting_subgraph.compile())  # 0Ek baar compile, node ki tarah
graph.add_node("report", report_subgraph.compile())  # Reporting Phase

graph.add_edge(START, "router")
graph.add_conditional_edges("router", route_intent, {
    "general_chat": "general_chat",
    "accounting": "accounting",
    "report": "report",
})
graph.add_edge("general_chat", END)
graph.add_edge("accounting", END)
graph.add_edge("report", END)

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