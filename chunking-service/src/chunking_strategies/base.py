from typing import Dict, List

Chunk = Dict[str, object]


class ChunkingStrategy:
    def chunk(
        self,
        *,
        text: str,
        file_id: int,
        workspace_id: int,
        s3_key: str,
        document_parser_version: str | None = None,
    ) -> List[Chunk]:
        raise NotImplementedError 