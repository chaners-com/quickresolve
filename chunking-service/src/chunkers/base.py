from typing import Dict, List

Chunk = Dict


class Chunker:
    def chunk(
        self, *, text: str, file_id: int, workspace_id: int, s3_key: str
    ) -> List[Chunk]:
        raise NotImplementedError
