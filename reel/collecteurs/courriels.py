"""The email channel of the REAL corpus: a real public mailing-list archive.

    python3 -m reel.collecteurs.courriels --mois 2025-06,2025-07,2025-08

The archive is the ASF's public Pony Mail (`lists.apache.org`), which serves a
real mbox per list and per month. Everything is real: the senders, the dates,
the threads, the attachments. And everything that identifies a person leaves at
ingestion - the sanitiser pseudonymises the structured fields **and** the free
text, using the real identities read from the headers (a signature at the
bottom of a message is exactly what a real corpus is full of).

Two real quantities the demo could only pretend to have:
  - `stratum` is the real list and the real month, so the published sample is
    stratified on something that exists;
  - `allers_retours` is the real size of the thread, counted from the real
    `References` / `In-Reply-To` headers.

The raw mbox is kept in `reel/brut/` (gitignored); only the sanitised artefact
is written to `reel/donnees/`.
"""

from __future__ import annotations

import argparse
import email.header
import email.utils
import gzip
import hashlib
import json
import mailbox
import re
import tempfile
from pathlib import Path
from typing import Any

from gisement.types.communs import Canal
from reel.collecteurs.commun import (
    BRUT,
    DONNEES,
    LONGUEUR_CORPS,
    assainir,
    ecrire_brut,
    ecrire_jsonl,
    horodatage,
    provenance,
)

BASE_REELLE = "https://lists.apache.org/api/mbox.lua"
LISTE = "dev"
DOMAINE = "kafka.apache.org"
SORTIE = DONNEES / "courriels" / "courriels.jsonl"
COUPES = re.compile(r"^\s*(>|\|)", re.M)
SIGNATURE = re.compile(r"^--\s*$", re.M)
BALISES = ("[DISCUSS]", "[VOTE]", "[RESULT]", "[ANNOUNCE]", "[KIP]", "[TODO]")
MOTIF_KIP = re.compile(r"\bKIP-(\d+)\b", re.I)


def url_mois(liste: str, domaine: str, mois: str) -> str:
    return f"{BASE_REELLE}?list={liste}&domain={domaine}&d={mois}"


def telecharger(urls: list[str]) -> list[bytes]:
    """The real mbox of each month, with a polite client."""
    from gisement.connecteurs import ClientHttpReel

    client = ClientHttpReel(entetes={"Accept": "application/mbox"}, timeout=90.0)
    return [client.get_bytes(url) for url in urls]


def lire_mbox(brut: bytes) -> list[Any]:
    """A real mbox -> the real messages, through the stdlib parser."""
    with tempfile.NamedTemporaryFile(suffix=".mbox", delete=False) as fichier:
        fichier.write(brut)
        chemin = Path(fichier.name)
    try:
        return list(mailbox.mbox(str(chemin)))
    finally:
        chemin.unlink(missing_ok=True)


def _decoder(valeur: Any) -> str:
    """A real header, decoded: `=?UTF-8?Q?...?=` is what a mailing list really
    sends, and an unreadable subject makes an unreadable fingerprint."""
    if valeur is None:
        return ""
    brut = str(valeur)
    morceaux = []
    for texte, encodage in email.header.decode_header(brut):
        if isinstance(texte, bytes):
            morceaux.append(texte.decode(encodage or "utf-8", errors="replace"))
        else:
            morceaux.append(texte)
    return " ".join(" ".join(morceaux).split())


def _adresses(message: Any, entete: str) -> list[str]:
    """The real addresses of one header, decoded."""
    return [
        adresse
        for brut in (message.get_all(entete) or [])
        for _, adresse in email.utils.getaddresses([_decoder(brut)])
        if adresse
    ]


def _corps(message: Any) -> str:
    """The real text body: plain text preferred, quotes and signature dropped."""
    if message.is_multipart():
        for partie in message.walk():
            if partie.get_content_type() == "text/plain":
                return _nettoyer(partie.get_payload(decode=True))
        return ""
    return _nettoyer(message.get_payload(decode=True))


def _nettoyer(brut: bytes | str | None) -> str:
    texte = brut.decode("utf-8", errors="replace") if isinstance(brut, bytes) else str(brut or "")
    texte = SIGNATURE.split(texte, maxsplit=1)[0]
    texte = COUPES.sub("", texte)
    return " ".join(texte.split())[:LONGUEUR_CORPS]


def _piece_jointe(message: Any) -> str:
    """The real attachment, reduced to its type: a real filename often carries
    a person's name, and the type is the only part the measure needs."""
    if not message.is_multipart():
        return ""
    for partie in message.walk():
        nom = partie.get_filename()
        if nom:
            return Path(str(nom)).suffix.lower().lstrip(".")[:10] or "binaire"
    return ""


def _fil(message: Any) -> str:
    """The real thread: the first `References`, else `In-Reply-To`, else subject."""
    for entete in ("references", "in-reply-to"):
        valeur = message.get(entete)
        if valeur:
            return str(valeur).split()[0].strip("<>")
    objet = re.sub(r"^((re|fwd?)\s*:\s*)+", "", str(message.get("subject", "")), flags=re.I)
    for balise in BALISES:
        objet = objet.replace(balise, "")
    return hashlib.sha1(" ".join(objet.lower().split()).encode()).hexdigest()[:16]


def _empreinte(valeur: str, prefixe: str) -> str:
    """A real Message-ID carries the sender's mail server - and often a gmail
    address. The corpus keeps a deterministic hash of it: the real thread
    structure survives, the identity does not."""
    return f"{prefixe}-{hashlib.sha1(valeur.encode('utf-8')).hexdigest()[:12]}"


def services_des_kips() -> dict[str, str]:
    """The real perimeter of each real KIP, read from the documents channel."""
    from gisement.serialisation import lire_json

    chemin = DONNEES / "documents" / "documents.json"
    if not chemin.exists():
        return {}
    documents = lire_json(chemin)
    return {str(d["id"]): str(d.get("service", "")) for d in documents if d.get("id")}


def normaliser(message: Any, mois: str, liste: str, kips: dict[str, str] | None = None) -> dict[str, Any]:
    """A real message -> the frozen email schema of CONTRACTS §5."""
    brut_id = str(message.get("message-id") or "").strip("<>") or (
        str(message.get("date", "")) + str(message.get("subject", ""))
    )
    identifiant = _empreinte(brut_id, "M")
    objet = _decoder(message.get("subject"))
    kip = MOTIF_KIP.search(objet)
    kip_ref = f"KIP-{kip.group(1)}" if kip else ""
    service = (kips or {}).get(kip_ref, "") or liste
    destinataires = _adresses(message, "to") + _adresses(message, "cc")
    return {
        "id": identifiant,
        "horodatage": _date_reelle(message.get("date")),
        "expediteur": email.utils.parseaddr(_decoder(message.get("from")))[1],
        "destinataires": destinataires,
        "objet": objet[:300],
        "corps": _corps(message),
        "service": service,
        "systeme": "mail",
        "kip": kip_ref,
        "stratum": f"{service}_{mois}",
        "piece_jointe": _piece_jointe(message),
        "fil": _empreinte(_fil(message), "F"),
        "balise": next((b for b in BALISES if b.lower() in objet.lower()), ""),
        "mois": mois,
        "provenance": "reel",
    }


def _date_reelle(valeur: Any) -> str:
    """A real `Date` header, including the broken ones, -> local ISO."""
    try:
        quand = email.utils.parsedate_to_datetime(str(valeur or ""))
    except (TypeError, ValueError):
        return ""
    if quand is None:
        return ""
    return horodatage(quand.astimezone().replace(tzinfo=None).isoformat())


def identites_reelles(bruts: list[dict[str, Any]]) -> tuple[str, ...]:
    """The real addresses, so they leave the bodies too."""
    vues: set[str] = set()
    for brut in bruts:
        for valeur in [brut.get("expediteur", ""), *brut.get("destinataires", [])]:
            if valeur:
                vues.add(str(valeur))
    return tuple(vues)


def allers_retours(bruts: list[dict[str, Any]]) -> None:
    """The real thread size, counted from the real headers."""
    par_fil: dict[str, int] = {}
    for brut in bruts:
        par_fil[brut["fil"]] = par_fil.get(brut["fil"], 0) + 1
    for brut in bruts:
        brut["allers_retours"] = max(0, par_fil[brut["fil"]] - 1)


def collecter(mois: list[str], liste: str, domaine: str, maximum: int) -> dict[str, Any]:
    """Download, normalise, sanitise, write. Returns the real figures."""
    urls = [url_mois(liste, domaine, m) for m in mois]
    archives = telecharger(urls)
    bruts: list[dict[str, Any]] = []
    kips = services_des_kips()
    noms: set[str] = set()
    for un_mois, archive in zip(mois, archives, strict=True):
        for message in lire_mbox(archive):
            if len(bruts) >= maximum:
                break
            for entete in ("from", "to", "cc"):
                for nom, _ in email.utils.getaddresses([_decoder(message.get(entete))]):
                    if nom:
                        noms.add(nom)
            bruts.append(normaliser(message, un_mois, liste, kips))
    allers_retours(bruts)
    chemin_brut = BRUT / "courriels_mbox.gz"
    chemin_brut.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(chemin_brut, "wb") as fichier:
        for archive in archives:
            fichier.write(archive)
    empreinte = hashlib.sha256(chemin_brut.read_bytes()).hexdigest()
    ecrire_brut("courriels.jsonl.gz", bruts)
    propres, detail = assainir(
        bruts,
        Canal.COURRIELS,
        tuple(sorted(set(identites_reelles(bruts)) | noms)),
        complement={
            "liste": f"{liste}@{domaine}",
            "mois": mois,
            "mbox_gz_sha256": empreinte,
            "dates_illisibles": sum(1 for b in bruts if not b["horodatage"]),
        },
    )
    detail["fils_reels"] = len({b["fil"] for b in propres})
    detail["strates"] = sorted({b["stratum"] for b in propres})
    ecrire_jsonl(SORTIE, propres)
    provenance(
        "courriels",
        f"archives publiques {liste}@{domaine}",
        BASE_REELLE,
        len(bruts),
        len(propres),
        empreinte,
    )
    return detail


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--liste", default=LISTE)
    parseur.add_argument("--domaine", default=DOMAINE)
    parseur.add_argument("--mois", default="2025-05,2025-06,2025-07,2025-08,2025-09,2025-10")
    parseur.add_argument("--max", type=int, default=2500)
    args = parseur.parse_args(argv)
    detail = collecter(args.mois.split(","), args.liste, args.domaine, args.max)
    print(json.dumps(detail, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
