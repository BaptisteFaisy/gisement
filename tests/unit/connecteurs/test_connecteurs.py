"""Idea #8 - real connectors, tested without a network."""

from __future__ import annotations

from pathlib import Path

from gisement.connecteurs import (
    FauxClientHttp,
    SourceJira,
    SourceSage,
    SourceServiceNow,
    paginer,
)

ISSUES = [
    {
        "key": "SUP-12",
        "fields": {
            "summary": "Recopier la commande fournisseur",
            "description": "commande 45892",
            "created": "2026-06-01T09:00:00.000+0200",
            "resolutiondate": "2026-06-01T09:20:00.000+0200",
            "assignee": {"displayName": "Marie Dupont"},
            "status": {"name": "Done"},
            "project": {"key": "SUP"},
            "comment": {"total": 3},
        },
    },
    {
        "key": "SUP-13",
        "fields": {
            "summary": "Relancer le devis",
            "created": "2026-06-02T10:00:00.000+0200",
            "status": {"name": "Open"},
            "project": {"key": "SUP"},
        },
    },
]


def test_jira_normalise_et_mesure_la_duree() -> None:
    client = FauxClientHttp(
        pages={"/rest/api/3/search?jql=project=SUP ORDER BY created&maxResults=100": ISSUES}
    )
    source = SourceJira(client, projet="SUP")
    tickets = list(source.lire())
    assert len(tickets) == 2
    premier = tickets[0]
    assert premier["id"] == "SUP-12"
    assert premier["sujet"] == "Recopier la commande fournisseur"
    assert premier["agent"] == "Marie Dupont"
    assert premier["systeme"] == "jira"
    assert premier["duree_traitement_minutes"] == 20.0
    assert tickets[1]["duree_traitement_minutes"] is None
    assert source.volume() == 2


def test_la_pagination_suit_le_curseur_et_s_arrete() -> None:
    client = FauxClientHttp(
        pages={"p1": [{"a": 1}], "p2": [{"a": 2}], "p3": [{"a": 3}]},
        liens={"p1": "p2", "p2": "p3", "p3": "p3"},  # curseur qui boucle
    )
    assert [b["a"] for b in paginer(client, "p1", max_pages=3)] == [1, 2, 3]
    assert len(client.appels) == 3, "un curseur infini doit s'arreter a max_pages"


def test_servicenow_normalise_la_table_incident() -> None:
    client = FauxClientHttp(
        pages={
            "/api/now/table/incident?sysparm_limit=100&sysparm_query=ORDERBYopened_at": [
                {
                    "number": "INC0001",
                    "short_description": "Verifier la coherence des montants",
                    "opened_at": "2026-06-03 08:00:00",
                    "assigned_to": {"name": "Paul Martin"},
                    "state": "2",
                },
            ]
        }
    )
    source = SourceServiceNow(client)
    incidents = list(source.lire())
    assert incidents[0]["id"] == "INC0001"
    assert incidents[0]["systeme"] == "servicenow"
    assert incidents[0]["agent"] == "Paul Martin"


def test_sage_lit_un_csv_fr_avec_point_virgule(tmp_path: Path) -> None:
    chemin = tmp_path / "export.csv"
    chemin.write_text(
        "Date;Operation;Compte;Montant;Utilisateur;Duree\n"
        "2026-06-01T09:00:00;Saisie commande;401000;1284,50;ADV-JOUR;540\n"
        "2026-06-01T10:00:00;Rapprochement BL;401000;900,00;COMPTA-AM;300\n",
        encoding="utf-8-sig",
    )
    lignes = list(SourceSage(chemin).lire())
    assert len(lignes) == 2
    assert lignes[0]["action"] == "Saisie commande"
    assert lignes[0]["duree_secondes"] == 540
    assert lignes[0]["systeme"] == "sage"


def test_sage_lit_un_csv_anglais_a_virgules(tmp_path: Path) -> None:
    chemin = tmp_path / "export_en.csv"
    chemin.write_text(
        "Date,Operation,Account,Amount,User,Duration\n"
        "2026-06-01T09:00:00,Key order,401000,1284.50,ADV-DAY,540\n",
        encoding="utf-8",
    )
    lignes = list(SourceSage(chemin).lire())
    assert lignes[0]["action"] == "Key order"
    assert lignes[0]["duree_secondes"] == 540


def test_un_fichier_absent_ne_casse_rien(tmp_path: Path) -> None:
    assert list(SourceSage(tmp_path / "inexistant.csv").lire()) == []
    assert SourceSage(tmp_path / "inexistant.csv").volume() == 0


def test_aucun_identifiant_ne_sort_du_connecteur() -> None:
    """R3 - the connector normalises; the pseudonymisation happens downstream."""
    client = FauxClientHttp(pages={"/x": ISSUES})
    tickets = list(paginer(client, "/x"))
    assert tickets[0]["fields"]["assignee"]["displayName"] == "Marie Dupont"
    from gisement.connecteurs.base import normaliser_ticket

    normalise = normaliser_ticket(tickets[0], "jira")
    assert "Marie Dupont" in normalise["agent"], "le connecteur transmet, il ne pseudonymise pas"
    from gisement.assainissement import assainir

    propre, _, _ = assainir(
        normalise,
        __import__("gisement.types", fromlist=["Canal"]).Canal.TICKETS,
        cle="cle",
        noms=("Marie Dupont",),
    )
    assert "Marie Dupont" not in str(propre)
