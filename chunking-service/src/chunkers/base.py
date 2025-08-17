from typing import Dict, List, Optional

Chunk = Dict


class Chunker:
    def chunk(
        self,
        *,
        text: str,
        file_id: int,
        workspace_id: int,
        s3_key: str,
        document_parser_version: Optional[str] = None,
    ) -> List[Chunk]:
        raise NotImplementedError
