import re


class QueryIntent:
    GENERAL = "general"
    REPOSITORY = "repository"


class QueryClassifier:
    """Decide whether a user query needs repository context.

    General conversational queries (greetings, identity questions,
    standalone code-generation requests) are answered without retrieval,
    while anything that plausibly targets repository contents is routed
    through vector search.
    """

    GREETING_RE = re.compile(
        r"^\s*(hi|hello|hey|yo|howdy|hiya|greetings|"
        r"good\s+(morning|afternoon|evening))\b",
        re.IGNORECASE,
    )

    IDENTITY_RE = re.compile(
        r"\b(who are you|what are you|what do you do|what can you do|"
        r"what are your capabilities|what can i ask you|"
        r"are you (an?\s+)?(ai|robot|bot|chatbot|human|assistant)|"
        r"what is your name|what'?s your name|do you have a name|"
        r"who made you|who created you|who built you|"
        r"introduce yourself|tell me about yourself|"
        r"what kind of (ai|assistant|model) are you)\b",
        re.IGNORECASE,
    )

    SMALL_TALK = {
        "thanks",
        "thank you",
        "thanks a lot",
        "thank you so much",
        "thank you very much",
        "ok",
        "okay",
        "ok thanks",
        "bye",
        "goodbye",
        "good bye",
        "see you",
        "see ya",
        "how are you",
        "how's it going",
        "what's up",
        "whats up",
        "nice to meet you",
    }

    SMALL_TALK_STARTS = (
        "thanks",
        "thank you",
        "bye",
        "goodbye",
        "see you",
    )

    GENERAL_REQUEST_RE = re.compile(
        r"^\s*(give me|write me|write an?|create an?|show me|"
        r"make an?|generate an?|produce an?|can you (write|create|make|"
        r"show|give|generate|produce)|how (do|can) i (write|create|make|"
        r"implement|generate)|implement an?)\b",
        re.IGNORECASE,
    )

    GENERAL_TOPIC_RE = re.compile(
        r"\b(c\+\+|c#|python|javascript|typescript|js|ts|java|go|"
        r"golang|rust|swift|kotlin|php|ruby|perl|scala|html|css|sql|"
        r"bash|shell|powershell|regex|function|snippet|script|program|"
        r"algorithm|helper|utility)\b",
        re.IGNORECASE,
    )

    REPOSITORY_REFERENCE_RE = re.compile(
        r"\b(this repo|the repo|this repository|the repository|"
        r"this codebase|the codebase|this project|the project|"
        r"this app|the app|our app|source code|the code|this code|"
        r"src/|lib/|package|module|directory|folder)\b",
        re.IGNORECASE,
    )

    FILE_LIKE_RE = re.compile(r"\.[a-zA-Z][\w-]*\b")

    def classify(self, query: str) -> str:
        text = " ".join(query.strip().lower().split())

        if not text:
            return QueryIntent.REPOSITORY

        if self.GREETING_RE.search(text):
            return QueryIntent.GENERAL

        if self.IDENTITY_RE.search(text):
            return QueryIntent.GENERAL

        if text in self.SMALL_TALK or text.startswith(self.SMALL_TALK_STARTS):
            return QueryIntent.GENERAL

        if (
            self.GENERAL_REQUEST_RE.search(text)
            and self.GENERAL_TOPIC_RE.search(text)
            and not self._references_repository(text)
        ):
            return QueryIntent.GENERAL

        return QueryIntent.REPOSITORY

    def _references_repository(self, text: str) -> bool:
        return bool(
            self.REPOSITORY_REFERENCE_RE.search(text)
            or self.FILE_LIKE_RE.search(text)
        )
