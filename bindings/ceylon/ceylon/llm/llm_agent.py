# from ceylon.ceylon import AgentCore, Processor, MessageHandler, AgentDefinition, MessageType
#
#
# class Agent(AgentCore, MessageHandler, Processor):
#     def __init__(self, name, position, instructions, responsibilities):
#         super().__init__(definition=AgentDefinition(
#             name=name,
#             position=position,
#             instructions=instructions,
#             responsibilities=responsibilities
#         ), on_message=self, processor=self)
#
#     async def on_message(self, agent_id, message):
#         dt = bytes(message.data)
#         print(id, name, dt.decode("utf-8"), message.originator_id, message.originator)
#
#     async def run(self, inputs):
#         definition = await self.definition()
#         print(f"{definition.name} run", inputs)
#         while True:
#             await self.broadcast(bytes("Hi from " + definition.name + " at " + str(time.time()), "utf-8"))
#             await asyncio.sleep(random.randint(1, 2))
