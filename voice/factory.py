from bridge.reply import Reply, ReplyType


class DummyVoice:
    def voiceToText(self, voice_file):
        return Reply(ReplyType.ERROR, "Voice recognition not implemented")

    def textToVoice(self, text):
        return Reply(ReplyType.ERROR, "Text to voice not implemented")


def create_voice(voice_type):
    return DummyVoice()
