import re

from google.cloud import firestore


def get_firestore_client(project_id: str | None = None) -> firestore.Client:
    return firestore.Client(project=project_id)


def safe_doc_id(*parts: str) -> str:
    return "__".join(_safe_part(part) for part in parts)


def next_counter(client, *scope: str) -> int:
    transaction = client.transaction()
    value = next_counter_in_transaction(client, transaction, *scope)
    _commit(transaction)
    return value


def next_counter_in_transaction(client, transaction, *scope: str) -> int:
    ref = client.collection("counters").document(safe_doc_id(*scope))
    snapshot = ref.get(transaction=transaction)
    data = snapshot.to_dict() if snapshot.exists else {}
    value = int(data.get("next_value", 1))
    transaction.set(
        ref,
        {
            "scope": list(scope),
            "next_value": value + 1,
        },
        merge=True,
    )
    return value


def snapshot_data(snapshot) -> dict | None:
    if not snapshot.exists:
        return None
    return snapshot.to_dict()


def _commit(transaction) -> None:
    commit = getattr(transaction, "commit", None)
    if commit is not None:
        commit()


def _safe_part(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return clean or "blank"
