from agentmind import AgentMindClient


client = AgentMindClient(
    base_url="https://agent-mind-apps-production.up.railway.app",
    api_key="agm_Bw74MLDmGdnWHMVdoXnIugGgBrPRqcf_p3leGr3lH60",
)

print("Health Check:")
print(client.health_check())

print("Manifest:")
print(client.get_manifest())

print("\nCurrent Agent:")
print(client.me())

print("\nTools:")
print(client.list_tools())

print("\nCalculator:")
print(
    client.run_tool(
        "calculator",
        {
            "expression": "45 * 12",
        },
    )
)

print("\nAgent Runtime:")
print(
    client.chat(
        task="What is 45 * 12?",
        memory_search_limit=5,
        save_result_to_memory=False,
    )
)