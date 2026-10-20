class ConversationService:
    def __init__(self):
        self.histories:dict[str,list[dict[str,str]]]={}

    def get_history(self,conversation_id:str)->list[dict[str,str]]:
        messages=self.histories.get(conversation_id,[])
        return [message.copy() for message in messages]

    def save_turn(
        self,
        conversation_id:str,
        question:str,
        answer:str
    ):
        if conversation_id not in self.histories:
            self.histories[conversation_id]=[]

        self.histories[conversation_id].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        
