"""Small positional tokenizer and recursive-descent parser for Search queries."""

from dataclasses import dataclass


class SearchSyntaxError(ValueError):
    def __init__(self, message, position, expected=()):
        super().__init__(message)
        self.position = position
        self.expected = tuple(expected)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class CompletionContext:
    kind: str
    prefix: str
    key: str | None
    replace_start: int
    replace_end: int


@dataclass(frozen=True)
class TextNode:
    value: str
    phrase: bool = False


@dataclass(frozen=True)
class KeyNode:
    key: str
    value: str
    phrase: bool = False
    start: int = 0


@dataclass(frozen=True)
class GenericInfoNode:
    type_name: str
    value: str


@dataclass(frozen=True)
class AndNode:
    children: tuple


@dataclass(frozen=True)
class OrNode:
    children: tuple


@dataclass(frozen=True)
class NotNode:
    child: object


def tokenize(source, *, tolerant=False):
    tokens = []
    index = 0
    punctuation = {":": "COLON", "=": "EQUAL", "(": "LPAREN", ")": "RPAREN"}
    while index < len(source):
        if source[index].isspace():
            index += 1
            continue
        start = index
        char = source[index]
        if char in punctuation:
            index += 1
            tokens.append(Token(punctuation[char], char, start, index))
        elif char == '"':
            index += 1
            value = []
            while index < len(source) and source[index] != '"':
                if source[index] == "\\":
                    index += 1
                    if index == len(source):
                        if not tolerant:
                            raise SearchSyntaxError("Unclosed quoted string", start, ('"',))
                        break
                value.append(source[index])
                index += 1
            if index == len(source) and not tolerant:
                raise SearchSyntaxError("Unclosed quoted string", start, ('"',))
            if index < len(source):
                index += 1
            tokens.append(Token("STRING", "".join(value), start, index))
        else:
            while index < len(source) and not source[index].isspace() and source[index] not in '"=:()':
                index += 1
            value = source[start:index]
            kind = value.upper() if value.upper() in ("AND", "OR", "NOT") else "WORD"
            tokens.append(Token(kind, value, start, index))
    tokens.append(Token("EOF", "", len(source), len(source)))
    return tuple(tokens)


def completion_context(source, cursor):
    """Classify only the token at the caret; normal parsing remains strict."""
    if not 0 <= cursor <= len(source):
        raise SearchSyntaxError("Cursor is outside the query", max(0, cursor))
    tokens = tokenize(source, tolerant=True)[:-1]
    current = next((token for token in tokens if token.start <= cursor < token.end and token.kind in ("WORD", "STRING")), None)
    if current is None:
        current = next((token for token in tokens if token.end == cursor and token.kind in ("WORD", "STRING")), None)
    before = [token for token in tokens if token.end <= (current.start if current else cursor)]
    previous = before[-1] if before else None
    start = current.start if current else cursor
    end = current.end if current else cursor
    prefix = source[start:cursor].lstrip('"') if current else ""
    if current and current.kind == "STRING" and cursor == end and source[end - 1] == '"' and previous:
        key = before[-2].value if len(before) >= 2 and before[-2].kind == "WORD" else None
        if previous.kind == "EQUAL" or previous.kind == "COLON" and key != "info":
            return CompletionContext("complete", "", None, cursor, cursor)
    if current and current.kind in ("WORD", "STRING") and previous and previous.kind == "COLON":
        key = before[-2].value if len(before) >= 2 and before[-2].kind == "WORD" else None
        if key == "info":
            following = next((token for token in tokens if token.start == end and token.kind == "EQUAL"), None)
            return CompletionContext("generic_info_type", prefix, key, start, following.end if following else end)
        return CompletionContext("value", prefix, key, start, end)
    if current and current.kind in ("WORD", "STRING") and previous and previous.kind == "EQUAL":
        return CompletionContext("generic_info_value", prefix, "info", start, end)
    if not current and previous and previous.kind == "COLON":
        key = before[-2].value if len(before) >= 2 and before[-2].kind == "WORD" else None
        return CompletionContext("generic_info_type" if key == "info" else "value", "", key, cursor, cursor)
    if not current and previous and previous.kind == "EQUAL":
        return CompletionContext("generic_info_value", "", "info", cursor, cursor)
    if current and current.kind == "WORD":
        following = next((token for token in tokens if token.start == end and token.kind == "COLON"), None)
        return CompletionContext("key", prefix, None, start, following.end if following else end)
    if not current and previous and previous.kind in ("AND", "OR", "NOT", "LPAREN"):
        return CompletionContext("key", "", None, cursor, cursor)
    if not current and previous and previous.kind in ("WORD", "STRING", "RPAREN"):
        return CompletionContext("operator", "", None, cursor, cursor)
    return CompletionContext("key", prefix, None, start, end)


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def take(self, kind):
        token = self.current
        if token.kind != kind:
            raise SearchSyntaxError(f"Expected {kind.lower()}", token.start, (kind,))
        self.index += 1
        return token

    def parse(self):
        if self.current.kind == "EOF":
            return None
        result = self.parse_or()
        self.take("EOF")
        return result

    def parse_or(self):
        nodes = [self.parse_and()]
        while self.current.kind == "OR":
            self.take("OR")
            nodes.append(self.parse_and())
        return OrNode(tuple(nodes)) if len(nodes) > 1 else nodes[0]

    def parse_and(self):
        nodes = [self.parse_not()]
        while self.current.kind == "AND":
            self.take("AND")
            nodes.append(self.parse_not())
        return AndNode(tuple(nodes)) if len(nodes) > 1 else nodes[0]

    def parse_not(self):
        if self.current.kind == "NOT":
            self.take("NOT")
            return NotNode(self.parse_not())
        if self.current.kind == "LPAREN":
            self.take("LPAREN")
            node = self.parse_or()
            self.take("RPAREN")
            return node
        return self.parse_atom()

    def parse_atom(self):
        first = self.current
        if first.kind not in ("WORD", "STRING"):
            raise SearchSyntaxError("Expected search term", first.start, ("WORD", "STRING"))
        self.index += 1
        if first.kind == "WORD" and self.current.kind == "COLON":
            self.take("COLON")
            value = self.current
            if value.kind not in ("WORD", "STRING") or not value.value:
                raise SearchSyntaxError("Expected value after ':'", value.start, ("WORD", "STRING"))
            self.index += 1
            if first.value.casefold() == "info":
                self.take("EQUAL")
                actual = self.current
                if actual.kind not in ("WORD", "STRING") or not actual.value:
                    raise SearchSyntaxError("Expected GenericInfo value", actual.start, ("WORD", "STRING"))
                self.index += 1
                return GenericInfoNode(value.value, actual.value)
            return KeyNode(first.value, value.value, value.kind == "STRING", first.start)
        if first.kind == "STRING":
            return TextNode(first.value, True)
        words = [first.value]
        while self.current.kind == "WORD" and self.tokens[self.index + 1].kind != "COLON":
            words.append(self.take("WORD").value)
        return TextNode(" ".join(words))


def parse(source):
    return Parser(source).parse()


def validate_keys(node, providers):
    """Resolve keys against the active registry; provider keys win collisions."""
    provider_keys = {provider.key for provider in providers}
    field_keys = {field.key for provider in providers for field in provider.fields}

    def visit(current):
        if isinstance(current, KeyNode) and current.key not in provider_keys | field_keys:
            raise SearchSyntaxError(f'Unknown search key "{current.key}"', current.start)
        if isinstance(current, (AndNode, OrNode)):
            for child in current.children:
                visit(child)
        if isinstance(current, NotNode):
            visit(current.child)

    visit(node)
