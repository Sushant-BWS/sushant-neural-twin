"""Resume PDF ingestion for the Sushant Neural Twin.

The loader converts a resume PDF into section-aware knowledge documents.
It does not invent information; it only reorganizes extracted resume text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader

from backend.knowledge.store import KnowledgeDocument


@dataclass(frozen=True)
class ResumeSection:
    """One logical section extracted from a resume."""

    name: str
    content: str


class ResumeKnowledgeLoader:
    """Extract and normalize resume information into knowledge documents."""

    SECTION_NAMES = (
        "PROFILE SUMMARY",
        "EDUCATION",
        "SKILLS",
        "EXPERIENCE",
        "PROJECTS",
        "ACHIEVEMENTS",
    )

    SECTION_CATEGORIES = {
        "PROFILE SUMMARY": "profile",
        "EDUCATION": "education",
        "SKILLS": "skills",
        "EXPERIENCE": "experience",
        "PROJECTS": "projects",
        "ACHIEVEMENTS": "achievements",
    }

    def load(self, path: str | Path) -> list[KnowledgeDocument]:
        """Read a resume PDF and return structured knowledge documents."""

        pdf_path = Path(path)

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"Resume file not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Expected a PDF resume: {pdf_path}"
            )

        text = self._extract_text(pdf_path)

        if not text.strip():
            raise ValueError(
                f"No readable text was extracted from resume: {pdf_path}"
            )

        sections = self._split_sections(text)

        documents: list[KnowledgeDocument] = []

        for index, section in enumerate(sections):
            documents.extend(
                self._section_to_documents(
                    section=section,
                    source_path=pdf_path,
                    section_index=index,
                )
            )

        return documents

    # =========================================================
    # PDF EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_text(path: Path) -> str:
        """Extract text from every PDF page."""

        reader = PdfReader(str(path))

        pages: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text() or ""

            if page_text.strip():
                pages.append(page_text)

        return "\n".join(pages)

    # =========================================================
    # SECTION DETECTION
    # =========================================================

    def _split_sections(self, text: str) -> list[ResumeSection]:
        """Split extracted resume text using known section headings."""

        normalized = self._normalize_lines(text)

        positions: list[tuple[int, str]] = []

        for section_name in self.SECTION_NAMES:
            match = re.search(
                rf"(?im)^{re.escape(section_name)}\s*$",
                normalized,
            )

            if match:
                positions.append(
                    (match.start(), section_name)
                )

        positions.sort(key=lambda item: item[0])

        sections: list[ResumeSection] = []

        for index, (start, section_name) in enumerate(positions):
            content_start = start + len(section_name)

            if index + 1 < len(positions):
                content_end = positions[index + 1][0]
            else:
                content_end = len(normalized)

            content = normalized[
                content_start:content_end
            ].strip()

            if content:
                sections.append(
                    ResumeSection(
                        name=section_name,
                        content=content,
                    )
                )

        return sections

    @staticmethod
    def _normalize_lines(text: str) -> str:
        """Normalize PDF extraction artifacts without changing meaning."""

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Fix common PDF line wrapping.
        text = re.sub(
            r"[ \t]+\n",
            "\n",
            text,
        )

        # Collapse excessive blank lines.
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    # =========================================================
    # SECTION → KNOWLEDGE DOCUMENTS
    # =========================================================

    def _section_to_documents(
        self,
        section: ResumeSection,
        source_path: Path,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Convert one resume section into searchable documents."""

        category = self.SECTION_CATEGORIES[
            section.name
        ]

        source = self._source_path(source_path)

        if category == "profile":
            return [
                self._document(
                    document_id=f"resume-profile-{section_index}",
                    content=section.content,
                    source=source,
                    category=category,
                    section=section.name,
                )
            ]

        if category == "education":
            return self._load_education(
                section,
                source,
                section_index,
            )

        if category == "skills":
            return self._load_skills(
                section,
                source,
                section_index,
            )

        if category == "experience":
            return self._load_experience(
                section,
                source,
                section_index,
            )

        if category == "projects":
            return self._load_projects(
                section,
                source,
                section_index,
            )

        if category == "achievements":
            return self._load_achievements(
                section,
                source,
                section_index,
            )

        return []

    # =========================================================
    # EDUCATION
    # =========================================================

    def _load_education(
        self,
        section: ResumeSection,
        source: str,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Create an education-specific knowledge document."""

        content = section.content

        return [
            self._document(
                document_id=f"resume-education-{section_index}",
                content=(
                    "Education: "
                    f"{self._clean_text(content)}"
                ),
                source=source,
                category="education",
                section=section.name,
            )
        ]

    # =========================================================
    # SKILLS
    # =========================================================

    def _load_skills(
        self,
        section: ResumeSection,
        source: str,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Create individual skill documents."""

        content = section.content

        # Extract the tools line from the resume.
        match = re.search(
            r"Tools:\s*(.+)",
            content,
            flags=re.IGNORECASE,
        )

        if not match:
            return [
                self._document(
                    document_id=f"resume-skills-{section_index}",
                    content=self._clean_text(content),
                    source=source,
                    category="skills",
                    section=section.name,
                )
            ]

        raw_skills = match.group(1)

        skills = [
            self._clean_text(skill)
            for skill in raw_skills.split(",")
            if self._clean_text(skill)
        ]

        documents: list[KnowledgeDocument] = []

        for index, skill in enumerate(skills):
            documents.append(
                self._document(
                    document_id=(
                        f"resume-skill-"
                        f"{section_index}-{index}"
                    ),
                    content=f"Technical skill: {skill}.",
                    source=source,
                    category="skills",
                    section=section.name,
                    metadata_extra={
                        "skill": skill,
                    },
                )
            )

        return documents

    # =========================================================
    # EXPERIENCE
    # =========================================================

    def _load_experience(
        self,
        section: ResumeSection,
        source: str,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Create experience documents from resume bullets."""

        lines = self._content_lines(section.content)

        if not lines:
            return []

        # Keep the complete experience section as one source-backed
        # document. This preserves all original resume details.
        content = " ".join(lines)

        return [
            self._document(
                document_id=f"resume-experience-{section_index}",
                content=content,
                source=source,
                category="experience",
                section=section.name,
            )
        ]

    # =========================================================
    # PROJECTS
    # =========================================================

    def _load_projects(
        self,
        section: ResumeSection,
        source: str,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Split the projects section into individual projects."""

        lines = self._content_lines(section.content)

        project_starts: list[int] = []

        for index, line in enumerate(lines):
            if self._looks_like_project_heading(line):
                project_starts.append(index)

        if not project_starts:
            return [
                self._document(
                    document_id=f"resume-projects-{section_index}",
                    content=" ".join(lines),
                    source=source,
                    category="projects",
                    section=section.name,
                )
            ]

        documents: list[KnowledgeDocument] = []

        for position, start in enumerate(project_starts):
            end = (
                project_starts[position + 1]
                if position + 1 < len(project_starts)
                else len(lines)
            )

            project_lines = lines[start:end]

            if not project_lines:
                continue

            project_name = self._clean_text(
                project_lines[0]
            )

            project_body = " ".join(
                project_lines[1:]
            ).strip()

            if project_body:
                content = (
                    f"Project: {project_name}. "
                    f"{project_body}"
                )
            else:
                content = f"Project: {project_name}."

            documents.append(
                self._document(
                    document_id=(
                        f"resume-project-"
                        f"{section_index}-{position}"
                    ),
                    content=content,
                    source=source,
                    category="projects",
                    section=section.name,
                    metadata_extra={
                        "project": project_name,
                    },
                )
            )

        return documents

    @staticmethod
    def _looks_like_project_heading(
        line: str,
    ) -> bool:
        """Identify project title lines from the extracted resume."""

        normalized = line.lower()

        known_projects = (
            "grafana-monitoring-stack",
            "serverless deployment on aws",
        )

        return any(
            project in normalized
            for project in known_projects
        )

    # =========================================================
    # ACHIEVEMENTS
    # =========================================================

    def _load_achievements(
        self,
        section: ResumeSection,
        source: str,
        section_index: int,
    ) -> list[KnowledgeDocument]:
        """Create one knowledge document per achievement."""

        lines = self._content_lines(
            section.content
        )

        documents: list[KnowledgeDocument] = []

        for index, line in enumerate(lines):
            cleaned = self._clean_text(line)

            if not cleaned:
                continue

            documents.append(
                self._document(
                    document_id=(
                        f"resume-achievement-"
                        f"{section_index}-{index}"
                    ),
                    content=cleaned,
                    source=source,
                    category="achievements",
                    section=section.name,
                )
            )

        return documents

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _content_lines(
        content: str,
    ) -> list[str]:
        """Return meaningful resume lines."""

        lines: list[str] = []

        for raw_line in content.splitlines():
            cleaned = ResumeKnowledgeLoader._clean_text(
                raw_line
            )

            if cleaned:
                lines.append(cleaned)

        return lines

    @staticmethod
    def _clean_text(value: str) -> str:
        """Normalize whitespace while preserving words."""

        value = value.replace("●", " ")
        value = value.replace("•", " ")
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    @staticmethod
    def _source_path(path: Path) -> str:
        """Return a stable project-relative source label."""

        normalized = path.as_posix()

        marker = "data/"

        if marker in normalized:
            return normalized[
                normalized.index(marker):
            ]

        return normalized

    @staticmethod
    def _document(
        document_id: str,
        content: str,
        source: str,
        category: str,
        section: str,
        metadata_extra: dict[str, str] | None = None,
    ) -> KnowledgeDocument:
        """Create a source-aware knowledge document."""

        metadata = {
            "source": source,
            "category": category,
            "section": section,
            "source_type": "resume",
        }

        if metadata_extra:
            metadata.update(metadata_extra)

        return KnowledgeDocument(
            id=document_id,
            content=content,
            metadata=metadata,
        )