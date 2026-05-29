"""Custom Test 序列读写兼容层。"""

from core.custom_test.serialization import (
    SequenceDocument as SequenceLoadResult,
    SequenceIssue,
    load_sequence,
    load_sequence_data,
    load_sequence_file,
    migrate_sequence,
    save_sequence,
    save_sequence_data,
    save_sequence_file,
)

__all__ = [
    "SequenceLoadResult",
    "SequenceIssue",
    "load_sequence",
    "load_sequence_data",
    "load_sequence_file",
    "migrate_sequence",
    "save_sequence",
    "save_sequence_data",
    "save_sequence_file",
]
