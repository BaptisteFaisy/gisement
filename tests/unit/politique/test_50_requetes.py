"""R7 (BLOCKING) - the 50 requests of the harness are all refused.

One single miss forbids the submission (spec 27). The same file feeds the
evaluation harness `eval/non_attribution.py`, so the test and the demo cannot
disagree.
"""

from __future__ import annotations

import pytest

from gisement.politique import cas_depuis_dict, charger_non_attribution, evaluer

CAS = charger_non_attribution()


def test_le_fichier_de_reference_contient_cinquante_requetes() -> None:
    assert len(CAS) == 50


def test_dix_huit_requetes_tentent_d_isoler_par_combinaison_de_filtres() -> None:
    assert sum(1 for c in CAS if c["nom"] == "combinaison de filtres") == 18


@pytest.mark.parametrize("brut", CAS, ids=[c["id"] for c in CAS])
def test_chaque_requete_est_refusee_avec_les_regles_attendues(brut: dict) -> None:
    identifiant, nom, requete, attendues, contexte = cas_depuis_dict(brut)
    decision = evaluer(requete, contexte)
    assert decision.refusee, f"{identifiant} ({nom}) a ete autorisee"
    obtenu = {r.value for r in decision.regles_violees}
    manquantes = set(attendues) - obtenu
    assert not manquantes, f"{identifiant} ({nom}) : regles absentes {sorted(manquantes)}"
    assert decision.motif, "un refus doit nommer la regle violee"
    assert decision.seuil_agregation >= 5


def test_aucune_requete_du_harnais_n_est_autorisee() -> None:
    autorisees = [c["id"] for c in CAS if evaluer(cas_depuis_dict(c)[2], cas_depuis_dict(c)[4]).autorisee]
    assert autorisees == []


def test_le_harnais_est_executable_et_rend_zero() -> None:
    import subprocess
    import sys
    from pathlib import Path

    racine = Path(__file__).resolve().parents[3]
    resultat = subprocess.run(
        [sys.executable, str(racine / "eval" / "non_attribution.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "50 requetes, 50 refusees" in resultat.stdout
    assert "18 par combinaison de filtres" in resultat.stdout
