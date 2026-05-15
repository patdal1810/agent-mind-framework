from agentmind import AgentMindClient


client = AgentMindClient(
    base_url="https://agent-mind-apps-production.up.railway.app",
    api_key="agm_V1J9OG2oLLxwOF9a-l5J-uvrNUg2yX70yWnpzkiQwZA",
)


print("Health Check:")
print(client.health_check())


print("\nDiscover All Agents:")
print(client.discover_agents())


print("\nDiscover Math Agents:")
math_agents = client.discover_agents(capability="math")
print(math_agents)


if math_agents["success"] and math_agents["result"]:
    target_agent_id = math_agents["result"][0]["id"]

    print("\nDelegate Task:")
    delegated = client.delegate_task(
        target_agent_id=target_agent_id,
        task="Solve x^2 - 5x + 6 = 0",
        memory_search_limit=5,
        save_result_to_memory=False,
    )
    print(delegated)

    task_id = delegated["result"]["task_id"]

    print("\nGet Task:")
    print(client.get_task(task_id))


print("\nList Completed Tasks:")
print(client.list_tasks(status="completed"))