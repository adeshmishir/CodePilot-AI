import re


class QueryIntent:
    GENERAL = "general"
    STRUCTURE_QUERY = "structure"
    FILE_LOOKUP_QUERY = "file_lookup"
    SEMANTIC_CODE_QUERY = "semantic_code"
    CROSS_FILE_QUERY = "cross_file"
    GENERAL_PROJECT_QUERY = "general_project"


# File extensions the classifier understands well enough to detect an
# explicit file path in a user query. Kept in sync with the supported
# extensions used by the repository parser.
FILE_EXTENSIONS = (
    r"py|pyw|pyi|js|jsx|mjs|cjs|ts|tsx|mts|cts|html|htm|css|scss|sass|"
    r"less|vue|svelte|json|yaml|yml|toml|ini|cfg|conf|java|kt|kts|scala|"
    r"groovy|gradle|c|h|cpp|cc|cxx|hpp|hh|cs|m|mm|go|rs|php|rb|swift|"
    r"dart|sh|bash|zsh|fish|sql|ex|exs|erl|hrl|hs|lhs|lua|r|ml|mli|pl|pm|"
    r"clj|cljs|md|mdx|rst|txt|tex"
)

FILE_PATH_EXTENSION = rf"[\w./\\-]+\.(?:{FILE_EXTENSIONS})\b"


class QueryClassifier:
    """Deterministically route a user query to a repository strategy.

    Intent         -> strategy
    ---------------   -------------------------------------------------
    STRUCTURE_QUERY  -> query the repository manifest (no embeddings)
    FILE_LOOKUP_QUERY-> exact manifest path lookup + that file's content
    SEMANTIC_CODE    -> vector retrieval
    CROSS_FILE_QUERY -> manifest file discovery + targeted retrieval
    GENERAL_PROJECT  -> manifest summary + config files + retrieval
    GENERAL          -> answered without repository context

    A query is classified by explicit, ordered patterns so that a broad
    question such as "what files are in the backend?" never falls into
    plain semantic retrieval.
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

    STRUCTURE_FILES_RE = re.compile(
        r"\b(?:what|which|how many)\s+files?\b"
        r"|\b(?:list|show|display|enumerate|print|name|see|get|find)\b"
        r".{0,40}\bfiles?\b"
        r"|\bfiles?\b.{0,15}\b(?:in|under|within|inside)\b"
        r"|\bhow many\s+(?:files?|folders?|directories?)\b",
        re.IGNORECASE,
    )

    STRUCTURE_TREE_RE = re.compile(
        r"\b(?:structure|tree|layout|hierarchy)\b"
        r"|\bwhat\s+(?:folders?|directories?)\b"
        r"|\b(?:folders?|directories?)\s+(?:exist|present|in|under|within)\b",
        re.IGNORECASE,
    )

    FILE_PATH_RE = re.compile(rf"\b{FILE_PATH_EXTENSION}", re.IGNORECASE)

    FILE_LOOKUP_RE = re.compile(
        rf"\b(?:show|read|display|open|view|get|fetch|print|explain|"
        rf"describe|tell me about|what does|what is|what'?s|where is|"
        rf"locate|look at|inspect|examine|contents of)\b.{{0,80}}"
        rf"{FILE_PATH_EXTENSION}",
        re.IGNORECASE,
    )

    CROSS_FILE_RE = re.compile(
        r"\b(?:communicat|interact|integrat|connected|connection|"
        r"between|data[\s-]?flow|request[\s-]?flow|request path|"
        r"end[\s-]?to[\s-]?end|pipeline|relationship|"
        r"\btwo\s+files|both\s+files|both\s+ends)\b"
        r"|\bfrontend\b.{0,60}\bbackend\b"
        r"|\bbackend\b.{0,60}\bfrontend\b"
        r"|\bfrom\s+[\w./-]+\s+(?:to|into|and)\b"
        r"|\bhow\s+does\b.{0,60}\b(?:call|fetch|send|serve|reach|talk|"
        r"route|talk to|pass)\b",
        re.IGNORECASE,
    )

    GENERAL_PROJECT_RE = re.compile(
        r"\b(?:technology|technologies|tech\s*stack|stack|"
        r"built with|made with|written in|frameworks? used|overview|"
        r"architecture|architectural|project overview|repo overview)\b"
        r"|\b(?:what is this|what does this|explain this|describe this|"
        r"tell me about this)\b.{0,40}\b(?:project|repo|repository|"
        r"app|application|codebase|system)\b"
        r"|\bhow does this project (?:work|function|fit together)\b",
        re.IGNORECASE,
    )

    def classify(self, query: str) -> str:
        text = " ".join(query.strip().lower().split())

        if not text:
            return QueryIntent.SEMANTIC_CODE_QUERY

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

        if self._is_structure_query(text):
            return QueryIntent.STRUCTURE_QUERY

        if self._is_file_lookup(text):
            return QueryIntent.FILE_LOOKUP_QUERY

        if self.CROSS_FILE_RE.search(text):
            return QueryIntent.CROSS_FILE_QUERY

        if self.GENERAL_PROJECT_RE.search(text):
            return QueryIntent.GENERAL_PROJECT_QUERY

        return QueryIntent.SEMANTIC_CODE_QUERY

    def extract_file_path(self, query: str) -> str | None:
        """Return the most likely repository file path in the query."""
        match = self.FILE_PATH_RE.search(query)

        if match is None:
            return None

        return match.group(0).rstrip(".,;:)")

    def _is_structure_query(self, text: str) -> bool:
        return bool(
            self.STRUCTURE_FILES_RE.search(text)
            or self.STRUCTURE_TREE_RE.search(text)
        )

    def _is_file_lookup(self, text: str) -> bool:
        return bool(
            self.FILE_LOOKUP_RE.search(text)
            or (
                self.FILE_PATH_RE.search(text)
                and self._is_lookup_only(text)
            )
        )

    def _is_lookup_only(self, text: str) -> bool:
        """Treat an explicit file path as a lookup when the query is
        short and contains no analysis verbs (e.g. ``main.py`` alone)."""
        has_analysis_verb = re.search(
            r"\b(how|why|bug|fix|break|error|performance|optimize|"
            r"compare|connect|flow|explain)\b",
            text,
        )

        return has_analysis_verb is None

    def _references_repository(self, text: str) -> bool:
        return bool(
            self.REPOSITORY_REFERENCE_RE.search(text)
            or self.FILE_LIKE_RE.search(text)
        )