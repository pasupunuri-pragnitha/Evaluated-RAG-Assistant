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
    with ~50 token overlap, ensures chunks never exceed the model's 512 token limit,
    and merges tiny/heading-only chunks (< 80 tokens) into sibling chunks.
    """

    def __init__(
        self,
        tokenizer: Any,
        target_tokens: int = 400,
        overlap_tokens: int = 50,
        max_tokens: int = 500,  # leaves headroom for special tokens [CLS], [SEP]
        min_tokens: int = 80,
    ):
        self.tokenizer = tokenizer
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
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
        # First break into paragraphs
        raw_units: List[str] = []
        for p in self._split_into_paragraphs(section_text):
            p_tokens = self.count_tokens(p)
            if p_tokens > self.target_tokens:
                # Break large paragraph into sentences
                sentences = self._split_into_sentences(p)
                for s in sentences:
                    s_tokens = self.count_tokens(s)
                    if s_tokens > self.target_tokens:
                        # Fallback for very long sentence: break by words
                        words = s.split()
                        sub_w: List[str] = []
                        for w in words:
                            sub_w.append(w)
                            if self.count_tokens(" ".join(sub_w)) >= self.target_tokens:
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

            # Gather units up to target_tokens
            unit_start_idx = idx
            while idx < n_units:
                unit = raw_units[idx]
                test_text = (
                    f"{accumulated_text}\n\n{unit}".strip()
                    if accumulated_text
                    else unit
                )
                test_tokens = self.count_tokens(test_text)

                if test_tokens > self.target_tokens and accumulated_units:
                    break

                if test_tokens > self.max_tokens and accumulated_units:
                    break

                accumulated_units.append(unit)
                accumulated_text = test_text
                current_tokens = test_tokens
                idx += 1

            full_content = accumulated_text.strip()
            total_tokens = self.count_tokens(full_content)

            # If total_tokens exceeds max_tokens, slice tokens directly
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

            if back_steps > 0:
                idx -= back_steps

        return chunks, current_index

    def _merge_tiny_chunks(self, chunks: List[ChunkData]) -> List[ChunkData]:
        """
        Merge heading-only or tiny chunks (< 80 tokens) into the next sibling chunk.
        If a tiny chunk is at the end of the document, merge into the previous chunk.
        """
        if not chunks:
            return []

        merged: List[ChunkData] = []
        pending_prefix = ""
        pending_heading = None

        for chunk in chunks:
            if pending_prefix:
                combined_content = f"{pending_prefix}\n\n{chunk.content}".strip()
                combined_tokens = self.count_tokens(combined_content)
                if combined_tokens <= self.max_tokens:
                    chunk = ChunkData(
                        chunk_index=0,
                        heading_path=chunk.heading_path or pending_heading or "",
                        content=combined_content,
                        token_count=combined_tokens,
                    )
                    pending_prefix = ""
                    pending_heading = None
                else:
                    # Could not merge without exceeding max_tokens, output pending
                    merged.append(
                        ChunkData(
                            chunk_index=0,
                            heading_path=pending_heading or "",
                            content=pending_prefix,
                            token_count=self.count_tokens(pending_prefix),
                        )
                    )
                    pending_prefix = ""
                    pending_heading = None

            if chunk.token_count < self.min_tokens:
                pending_prefix = chunk.content
                pending_heading = chunk.heading_path
            else:
                merged.append(chunk)

        # Handle any leftover pending chunk at the end
        if pending_prefix:
            if merged:
                last = merged[-1]
                combined_content = f"{last.content}\n\n{pending_prefix}".strip()
                combined_tokens = self.count_tokens(combined_content)
                if combined_tokens <= self.max_tokens:
                    merged[-1] = ChunkData(
                        chunk_index=0,
                        heading_path=last.heading_path,
                        content=combined_content,
                        token_count=combined_tokens,
                    )
                else:
                    merged.append(
                        ChunkData(
                            chunk_index=0,
                            heading_path=pending_heading or "",
                            content=pending_prefix,
                            token_count=self.count_tokens(pending_prefix),
                        )
                    )
            else:
                # Whole document was smaller than min_tokens
                merged.append(
                    ChunkData(
                        chunk_index=0,
                        heading_path=pending_heading or "",
                        content=pending_prefix,
                        token_count=self.count_tokens(pending_prefix),
                    )
                )

        # Re-index sequentially
        for idx, c in enumerate(merged):
            c.chunk_index = idx

        return merged

    def chunk_document(
        self, markdown_content: str, default_title: str = "Overview"
    ) -> List[ChunkData]:
        """
        Parses markdown content by heading hierarchy, chunks, and merges tiny chunks.
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

        in_fence = False
        fence_marker = ""

        for line in lines:
            stripped = line.strip()
            # Track code fence state (``` or ~~~)
            if stripped.startswith("```") or stripped.startswith("~~~"):
                marker = stripped[:3]
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                    fence_marker = ""

            match = heading_regex.match(stripped) if not in_fence else None
            if match:
                # Save previous section if it has non-whitespace content
                section_text = "\n".join(current_lines).strip()
                heading_path = get_current_heading_path()
                # Exclude purely promotional/testimonial sections like "Opinions"
                if section_text and not heading_path.endswith("Opinions"):
                    sections.append((heading_path, section_text))
                current_lines = []

                level = len(match.group(1))
                heading_title = match.group(2).strip()
                heading_title = re.sub(r"\{[^{}]*\}", "", heading_title).strip()

                # Pop headings of deeper or equal level
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()

                heading_stack.append((level, heading_title))
            else:
                current_lines.append(line)

        # Add the final section
        final_text = "\n".join(current_lines).strip()
        final_heading_path = get_current_heading_path()
        if final_text and not final_heading_path.endswith("Opinions"):
            sections.append((final_heading_path, final_text))

        # If document had no sections, fallback to whole document
        if not sections and default_title:
            cleaned = markdown_content.strip()
            if cleaned:
                sections.append((default_title, cleaned))

        initial_chunks: List[ChunkData] = []
        chunk_idx = 0

        for heading_path, text in sections:
            if not text:
                continue

            clean_text = text.strip()
            total_tokens = self.count_tokens(clean_text)

            if total_tokens <= self.target_tokens:
                initial_chunks.append(
                    ChunkData(
                        chunk_index=chunk_idx,
                        heading_path=heading_path,
                        content=clean_text,
                        token_count=total_tokens,
                    )
                )
                chunk_idx += 1
            else:
                sub_chunks, chunk_idx = self._create_overlapping_subchunks(
                    heading_path=heading_path,
                    section_text=clean_text,
                    start_index=chunk_idx,
                )
                initial_chunks.extend(sub_chunks)

        # Merge tiny chunks (< 80 tokens) into sibling chunks
        final_chunks = self._merge_tiny_chunks(initial_chunks)
        return final_chunks
