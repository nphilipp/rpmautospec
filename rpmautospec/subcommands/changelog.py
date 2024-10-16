from typing import Any, Optional, Union

from .. import pager
from ..exc import SpecParseFailure
from ..pkg_history import PkgHistoryProcessor


def register_subcommand(subparsers):
    subcmd_name = "generate-changelog"

    gen_changelog_parser = subparsers.add_parser(
        subcmd_name,
        help="Generate changelog entries from git commit logs",
    )

    gen_changelog_parser.add_argument(
        "spec_or_path",
        default=".",
        nargs="?",
        help="Path to package worktree or the spec file within",
    )

    return subcmd_name


def _coerce_to_str(str_or_bytes: Union[str, bytes]) -> str:
    if isinstance(str_or_bytes, bytes):
        str_or_bytes = str_or_bytes.decode("utf-8", errors="replace")
    return str_or_bytes


def _coerce_to_bytes(str_or_bytes: Union[str, bytes]) -> str:
    if isinstance(str_or_bytes, str):
        str_or_bytes = str_or_bytes.encode("utf-8")
    return str_or_bytes


def collate_changelog(
    processor_results: dict[str, Any], result_type: Optional[type] = str
) -> Union[str, bytes]:
    changelog = processor_results["changelog"]
    if result_type == str:
        entry_strings = (_coerce_to_str(entry.format()) for entry in changelog)
    else:
        entry_strings = (_coerce_to_bytes(entry.format()) for entry in changelog)
    return "\n\n".join(entry_strings)


def produce_changelog(spec_or_repo, *, error_on_unparseable_spec: bool):
    processor = PkgHistoryProcessor(spec_or_repo)
    result = processor.run(visitors=(processor.release_number_visitor, processor.changelog_visitor))
    if error_on_unparseable_spec and result["epoch-version"] is None:
        # If epoch-version is None, this indicates that the spec file couldn’t be parsed.
        raise SpecParseFailure(f"Couldn’t parse spec file {processor.specfile.name}")
    return collate_changelog(result)


def main(args):
    """Main method."""
    changelog = produce_changelog(
        args.spec_or_path, error_on_unparseable_spec=args.error_on_unparseable_spec
    )
    pager.page(changelog, enabled=args.pager)
