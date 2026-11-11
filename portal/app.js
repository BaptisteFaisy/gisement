/* Gisement - portal. Every call carries the bearer token; the tenant comes
   from it, never from a parameter (EF-71). Every measure goes through the
   gateway policy (R5). */
const JETON = () => document.getElementById("jeton").value;

async function api(chemin, options = {}) {
  const reponse = await fetch(chemin, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${JETON()}`,
      ...(options.headers || {}),
    },
  });
  const corps = await reponse.json();
  return { statut: reponse.status, corps };
}

function element(id) { return document.getElementById(id); }
function html(valeur) {
  return String(valeur ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

async function majEtat() {
  const { corps } = await api("/api/health");
  const valide = corps.donnees?.conformite_validee;
  element("etat-conformite").innerHTML =
    `Validation DPO : <strong>${valide ? "enregistree" : "non enregistree"}</strong>` +
    ` - etat de la campagne : <strong>${html(corps.donnees?.statut_campagne)}</strong>`;
  element("btn-lancer").disabled = !valide || corps.donnees?.mesure_lancee;
  element("btn-suspendre").disabled = !valide;
}

async function lancer() {
  const { statut, corps } = await api("/api/campagnes/courante/lancer", { method: "POST" });
  if (!corps.ok) { element("mesure").textContent = corps.erreur; return; }
  await afficherMesure();
  await majEtat();
}

async function afficherMesure() {
  const { corps } = await api("/api/campagnes/courante");
  if (!corps.ok) { element("mesure").textContent = corps.erreur; return; }
  const d = corps.donnees;
  element("mesure").innerHTML = `
    <div class="ligne"><span class="nom">${d.activites} activites mesurees</span>
      <span class="detail">${d.groupes} groupes, ${d.motifs} motifs, ${d.revue_humaine} en revue humaine</span></div>
    <div class="ligne"><span class="nom">Gisement net annuel</span>
      <span class="detail">${d.gisement_net_annuel} EUR sur les processus identifies</span></div>
    <div class="ligne"><span class="nom">Cout mesure de la campagne</span>
      <span class="detail">${d.cout_mesure_usd} USD</span></div>`;
  element("couverture").innerHTML = `<strong>${html(d.couverture)}</strong><br>` +
    `<span class="detail">${(d.couverture_par_canal || []).join(" | ")}</span>`;
  await afficherVagues();
  await afficherReference();
  await afficherDecconseilles();
}

async function afficherVagues() {
  const { corps } = await api("/api/projets");
  if (!corps.ok) return;
  const d = corps.donnees;
  const titres = { vague_1: "Vague 1 - amorcage", vague_2: "Vague 2 - structurel",
    vague_3: "Vague 3 - transformation", aucune: "Reserve (projets classes, hors vagues)" };
  let html = "";
  for (const vague of ["vague_1", "vague_2", "vague_3", "aucune"]) {
    const projets = d.projets.filter((p) => p.vague === vague);
    if (!projets.length) continue;
    html += `<div class="vague">${titres[vague]}</div>`;
    for (const p of projets) {
      html += `<div class="ligne"><span class="nom">${p.rang ? p.rang + ". " : ""}${p.processus_id} [${p.type}]</span>
        <span class="detail">${p.gain_mensuel} EUR/mois - retour ${p.delai_retour_mois} mois - risque ${p.risque}</span></div>`;
    }
  }
  if (!d.vague1_existe) html += `<div class="ligne"><span class="nom">Vague 1 impossible</span>
    <span class="detail">${html(d.recommandation_elargissement)}</span></div>`;
  element("vagues").innerHTML = html;
}

async function afficherReference() {
  const { corps } = await api("/api/gisements/P-07");
  if (!corps.ok) return;
  const d = corps.donnees;
  element("reference").innerHTML = `
    <table><tr><th>Calcul naif</th><th>Gisement</th></tr>
    <tr><td>${d.gain_naif_mensuel} EUR/mois</td><td>${d.gain_mensuel} EUR/mois</td></tr>
    <tr><td>temps net : ${d.temps_net} h/mois [${d.intervalle[0]} - ${d.intervalle[1]}]</td>
    <td>facteur de surestimation : <strong>${d.ecart_naif}</strong> - retour ${d.delai_retour_mois} mois</td></tr></table>`;
}

async function afficherDecconseilles() {
  const { corps } = await api("/api/deconseilles");
  if (!corps.ok) return;
  element("deconseilles").innerHTML = corps.donnees.map((d) =>
    `<div class="ligne"><span class="nom">${d.processus_id}</span>
      <span class="detail">${html(d.motif)} - ${html(d.seuil_atteint)}<br>${html(d.condition_reexamen)}</span></div>`
  ).join("");
}

async function demanderMesure(individuel) {
  const corps = await api("/api/mesure", {
    method: "POST",
    body: JSON.stringify(individuel
      ? { canal: "tickets", groupements: ["service", "individu"], taille_groupe: 1,
          taille_resultat_apres_filtres: 1, filtres: { service: "adv" } }
      : { canal: "tickets", groupements: ["service", "motif"], taille_groupe: 34,
          taille_resultat_apres_filtres: 34, filtres: { service: "adv" } }),
  });
  const verdict = element("verdict");
  if (corps.corps.ok) {
    verdict.className = "verdict autorise";
    verdict.textContent = `AUTORISE - ${JSON.stringify(corps.corps.donnees)}`;
  } else {
    verdict.className = "verdict refus";
    verdict.textContent =
      `REFUSE (${corps.statut}) - regles violees : ${(corps.corps.regles_violees || []).join(", ")}\n` +
      `${corps.corps.erreur}`;
  }
}

async function afficherDocument(chemin) {
  const { corps } = await api(chemin);
  element("document").className = "verdict";
  element("document").textContent = corps.donnees
    ? (corps.donnees.rapport || corps.donnees.registre || JSON.stringify(corps.donnees, null, 2))
    : corps.erreur;
}

document.getElementById("btn-conformite").addEventListener("click", async () => {
  await api("/api/campagnes/courante/conformite", { method: "POST", body: JSON.stringify({}) });
  await majEtat();
});
document.getElementById("btn-lancer").addEventListener("click", lancer);
document.getElementById("btn-suspendre").addEventListener("click", async () => {
  await api("/api/campagnes/courante/suspendre", { method: "POST" });
  await majEtat();
});
document.getElementById("btn-individuel").addEventListener("click", () => demanderMesure(true));
document.getElementById("btn-agregat").addEventListener("click", () => demanderMesure(false));
document.getElementById("btn-rapport").addEventListener("click", () => afficherDocument("/api/rapports/CMP-0031?langue=fr"));
document.getElementById("btn-registre").addEventListener("click", () => afficherDocument("/api/registre-conformite/CMP-0031?langue=fr"));
document.getElementById("btn-budget").addEventListener("click", () => afficherDocument("/api/budget"));
document.getElementById("jeton").addEventListener("change", majEtat);
majEtat();
