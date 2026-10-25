import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass
class ChunkData:
    chunk_index: int
    heading_path: str
    content: str
    token_count: int


class MarkdownHeadingChunker:
    """
    Chunks Markdown documents by heading hierarchy, maintaining ~400 token chunks
    with ~50 token overlap, and ensures chunks never exceed the model's 512 token limit.
    """

    def __init__(
        self,
        tokenizer: Any,
        target_tokens: int = 400,
        overlap_tokens: int = 50,
        max_tokens: int = 500,  # leaves headroom for special tokens [CLS], [SEP]
    ):
        self.tokenizer = tokenizer
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def _split_into_paragraphs(self, text: str) -> List[str]:
        # Split by double newline, preserving structure
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return paragraphs

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split text into sentences using punctuation boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_overlapping_subchunks(
        self,
        heading_path: str,
        section_text: str,
        start_index: int,
    ) -> Tuple[List[ChunkData], int]:
        prefix = f"[{heading_path}]\n\n"
        prefix_tokens = self.count_tokens(prefix)
        effective_target = max(self.target_tokens - prefix_tokens, 100)
        effective_max = max(self.max_tokens - prefix_tokens, 150)

        # First break into paragraphs
        raw_units: List[str] = []
        for p in self._split_into_paragraphs(section_text):
            p_tokens = self.count_tokens(p)
            if p_tokens > effective_target:
                # Break large paragraph into sentences
                sentences = self._split_into_sentences(p)
                for s in sentences:
                    s_tokens = self.count_tokens(s)
                    if s_tokens > effective_target:
                        # Fallback for very long sentence: break by words
                        words = s.split()
                        sub_w: List[str] = []
                        for w in words:
                            sub_w.append(w)
                            if self.count_tokens(" ".join(sub_w)) >= effective_target:
                                raw_units.append(" ".join(sub_w))
                                sub_w = []
                        if sub_w:
                            raw_units.append(" ".join(sub_w))
                    else:
                        raw_units.append(s)
            else:
                raw_units.append(p)

        if not raw_units:
            return [], start_index

        chunks: List[ChunkData] = []
        current_index = start_index

        idx = 0
        n_units = len(raw_units)

        while idx < n_units:
            accumulated_units: List[str] = []
            accumulated_text = ""
            current_tokens = 0

            # Gather units up to effective_target
            unit_start_idx = idx
            while idx < n_units:
                unit = raw_units[idx]
                test_text = (
                    f"{accumulated_text}\n\n{unit}".strip()
                    if accumulated_text
                    else unit
                )
                test_tokens = self.count_tokens(test_text)

                if test_tokens > effective_target and accumulated_units:
                    break

                if test_tokens > effective_max and accumulated_units:
                    break

                accumulated_units.append(unit)
                accumulated_text = test_text
                current_tokens = test_tokens
                idx += 1

            full_content = f"{prefix}{accumulated_text}".strip()
            total_tokens = self.count_tokens(full_content)

            # If by any chance total_tokens still exceeds max_tokens, truncate tokens directly
            if total_tokens > self.max_tokens:
                encoded_ids = self.tokenizer.encode(
                    full_content, add_special_tokens=False
                )[: self.max_tokens]
                full_content = self.tokenizer.decode(
                    encoded_ids, skip_special_tokens=True
                )
                total_tokens = len(encoded_ids)

            chunks.append(
                ChunkData(
                    chunk_index=current_index,
                    heading_path=heading_path,
                    content=full_content,
                    token_count=total_tokens,
                )
            )
            current_index += 1

            if idx >= n_units:
                break

            # Overlap calculation: walk backwards to find ~overlap_tokens
            overlap_accum = 0
            back_steps = 0
            for back_idx in range(idx - 1, unit_start_idx, -1):
                unit_tokens = self.count_tokens(raw_units[back_idx])
                if overlap_accum + unit_tokens <= self.overlap_tokens:
                    overlap_accum += unit_tokens
                    back_steps += 1
                else:
                    break

            # Reposition idx backwards by back_steps for overlap
            if back_steps > 0:
                idx -= back_steps

        return chunks, current_index

    def chunk_document(
        self, markdown_content: str, default_title: str = "Overview"
    ) -> List[ChunkData]:
        """
        Parses markdown content by heading hierarchy and produces chunks.
        """
        heading_regex = re.compile(r"^(#{1,6})\s+(.+)$")
        lines = markdown_content.splitlines()

        sections: List[Tuple[str, str]] = []  # (heading_path, text)
        heading_stack: List[Tuple[int, str]] = []  # (level, heading_text)
        current_lines: List[str] = []

        def get_current_heading_path() -> str:
            if not heading_stack:
                return default_title
            return " > ".join(title for _, title in heading_stack)

        for line in lines:
            match = heading_regex.match(line.strip())
            if match:
                # Save previous section if it has non-whitespace content
                section_text = "\n".join(current_lines).strip()
                if section_text:
                    sections.append((get_current_heading_path(), section_text))
                current_lines = []

                level = len(match.group(1))
                heading_title = match.group(2).strip()

                # Pop headings of deeper or equal level
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()

                heading_stack.append((level, heading_title))
            else:
                current_lines.append(line)

        # Add the final section
        final_text = "\n".join(current_lines).strip()
        if final_text:
            sections.append((get_current_heading_path(), final_text))

        # If document had no sections (e.g. empty or only title), handle gracefully
        if not sections and default_title:
            sections.append((default_title, markdown_content.strip()))

        # Now chunk each section
        chunks: List[ChunkData] = []
        chunk_idx = 0

        for heading_path, text in sections:
            if not text:
                continue

            content_with_prefix = f"[{heading_path}]\n\n{text}".strip()
            total_tokens = self.count_tokens(content_with_prefix)

            if total_tokens <= self.target_tokens:
                chunks.append(
                    ChunkData(
                        chunk_index=chunk_idx,
                        heading_path=heading_path,
                        content=content_with_prefix,
                        token_count=total_tokens,
                    )
                )
                chunk_idx += 1
            else:
                sub_chunks, chunk_idx = self._create_overlapping_subchunks(
                    heading_path=heading_path,
                    section_text=text,
                    start_index=chunk_idx,
                )
                chunks.extend(sub_chunks)

        return chunks
