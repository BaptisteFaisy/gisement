/* Gisement - portal core.
 *
 * Two runtimes, one front-end:
 *  - LIVE   : the JSON API answers (local `gisement serve`, or the deployed
 *             Lambda behind API Gateway). Every call carries the bearer token;
 *             the tenant comes from it, never from a parameter (EF-71), and
 *             every measure goes through the gateway policy (R5).
 *  - STATIC : GitHub Pages, no backend. The pre-computed responses of
 *             data/api.json are served instead and the demo flow (DPO
 *             validation -> launch -> suspend) is driven client-side. The
 *             figures are the real ones, produced by the pipeline.
 *
 * The section renderers live in vues.js.
 */
let STATIQUE = null;
let etatLocal = { conforme: false, lance: false, suspendu: false };
let sectionCourante = "conformite";
/* The identifiers of the corpus on screen: the demo (P-07, CMP-0031) or the
   real one (Apache Kafka). They come from the pre-computed responses, never
   from a hard-coded route. */
let CONFIG = { corpus: "demo", campagne: "CMP-0031", processus: "P-07", titre: "Demo synthetique" };

const JETON = () => document.getElementById("jeton").value;
const element = (id) => document.getElementById(id);

function escape(valeur) {
  return String(valeur ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(chemin, options = {}) {
  if (STATIQUE !== null) return apiStatique(chemin, options);
  try {
    const reponse = await fetch(chemin, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${JETON()}`,
        ...(options.headers || {}),
      },
    });
    return { statut: reponse.status, corps: await reponse.json() };
  } catch (erreur) {
    return { statut: 0, corps: { ok: false, erreur: String(erreur) } };
  }
}

function apiStatique(chemin, options) {
  const methode = (options.method || "GET").toUpperCase();
  let clef = `${methode} ${chemin}`;
  if (chemin === "/api/mesure") {
    const corps = JSON.parse(options.body || "{}");
    const taille = Math.min(
      corps.taille_groupe ?? 0,
      corps.taille_resultat_apres_filtres ?? corps.taille_groupe ?? 0);
    if ((corps.groupements || []).includes("individu")) clef += "#individu";
    else if (taille < 5) clef += "#filtres";
    else clef += "#agrege";
  }
  if (chemin === "/api/health") return { statut: 200, corps: { ok: true, donnees: santeLocale() } };
  const reponse = STATIQUE[clef];
  if (reponse) return { statut: reponse.statut, corps: reponse.corps };
  return { statut: 404, corps: { ok: false, erreur: `route statique inconnue : ${clef}` } };
}

function santeLocale() {
  return {
    statut: "en_ligne", campagne: CONFIG.campagne,
    statut_campagne: etatLocal.suspendu ? "suspendue"
      : etatLocal.lance ? "terminee" : etatLocal.conforme ? "prete" : "brouillon",
    conformite_validee: etatLocal.conforme && !etatLocal.suspendu,
    mesure_lancee: etatLocal.lance,
  };
}

/* ------------------------------------------------------------------ demo flow */

async function majNav() {
  // The section titles follow the corpus on screen: the demo has 23
  // processes, the real corpus the number it really measured. In live mode
  // this is also the only place that learns the reference process: the demo's
  // P-07 does not exist on the real corpus (R-01..R-12).
  const { corps } = await api("/api/processus");
  const bouton = element("nav-processus");
  if (!bouton || !corps.ok) return;
  const nombre = corps.donnees.nb_processus;
  if (nombre) bouton.textContent = `5. Les ${nombre} processus`;
  const ids = (corps.donnees.processus || []).map((p) => p.id);
  if (ids.length && !ids.includes(CONFIG.processus)) CONFIG.processus = ids[0];
}

function estDpo() {
  return JETON() === "jeton-demo-dpo";
}

async function majEtat() {
  const { corps } = await api("/api/health");
  const d = corps.donnees || {};
  const valide = d.conformite_validee && !etatLocal.suspendu;
  const dpo = estDpo();
  const etat = element("etat-campagne");
  if (etat) {
    etat.innerHTML =
      `Validation DPO : <strong>${d.conformite_validee ? "enregistree" : "non enregistree"}</strong>` +
      ` &middot; campagne : <strong>${escape(d.statut_campagne)}</strong>` +
      ` &middot; mesure : <strong>${d.mesure_lancee ? "faite" : "non lancee"}</strong>`;
  }
  document.querySelectorAll("[data-action]").forEach((bouton) => {
    const action = bouton.dataset.action;
    // The role selected in the header really gates the buttons: the DPO
    // validates and suspends, the MSP and the DPO launch. The server already
    // refuses the rest; the UI must not advertise a power the role lacks.
    if (action === "conformite") bouton.disabled = !dpo;
    if (action === "lancer") bouton.disabled = !valide || d.mesure_lancee || !(dpo || JETON() === "jeton-demo-msp");
    if (action === "suspendre") bouton.disabled = !valide || !dpo;
    if (action === "reprendre") bouton.disabled = !etatLocal.suspendu || !dpo;
  });
}

async function enregistrerConformite() {
  if (STATIQUE !== null) { etatLocal.conforme = true; etatLocal.suspendu = false; }
  await api("/api/campagnes/courante/conformite", { method: "POST", body: JSON.stringify({}) });
  await majEtat();
  await majNav();
  await afficher(sectionCourante);
}

async function lancer() {
  if (STATIQUE !== null) etatLocal.lance = true;
  const { corps } = await api("/api/campagnes/courante/lancer", { method: "POST" });
  await majEtat();
  if (!corps.ok && STATIQUE === null) {
    rendre(`<h2>Mesure refusee</h2><p class="refus">${escape(corps.erreur)}</p>`);
    return;
  }
  await majNav();
  await afficher("mesure");
}

async function suspendre() {
  if (STATIQUE !== null) etatLocal.suspendu = true;
  await api("/api/campagnes/courante/suspendre", { method: "POST" });
  await majEtat();
  await majNav();
  await afficher(sectionCourante);
}

async function reprendre() {
  if (STATIQUE !== null) etatLocal.suspendu = false;
  else await api("/api/campagnes/courante/conformite", { method: "POST", body: JSON.stringify({}) });
  await majEtat();
  await majNav();
  await afficher(sectionCourante);
}

async function demanderMesure(individuel) {
  const { statut, corps } = await api("/api/mesure", {
    method: "POST",
    body: JSON.stringify(individuel
      ? { canal: "tickets", groupements: ["service", "individu"], taille_groupe: 1,
          taille_resultat_apres_filtres: 1, filtres: { service: "adv" } }
      : { canal: "tickets", groupements: ["service", "motif"], taille_groupe: 34,
          taille_resultat_apres_filtres: 34, filtres: { service: "adv" } }),
  });
  const cible = element("verdict");
  if (!cible) return;
  if (corps.ok) {
    cible.className = "verdict autorise";
    cible.textContent = `AUTORISE (${statut}) - ${JSON.stringify(corps.donnees)}`;
  } else {
    cible.className = "verdict refus";
    cible.textContent =
      `REFUSE (${statut}) - regles violees : ${(corps.regles_violees || []).join(", ")}\n` +
      `${corps.erreur}`;
  }
}

/* ------------------------------------------------------------------ navigation */

let renduEnCours = 0;  // Render token: a slow view must not paint over the chosen one.

function rendre(html) {
  element("contenu").innerHTML = html;
}

async function afficher(section) {
  const jeton = ++renduEnCours;
  sectionCourante = section;
  document.querySelectorAll(".nav button").forEach((b) =>
    b.classList.toggle("actif", b.dataset.section === section));
  const rendu = VUES[section];
  if (!rendu) { renduEnCours === jeton && rendre(`<h2>Section inconnue</h2>`); return; }
  if (jeton === renduEnCours) rendre("<h2>Chargement…</h2>");
  try {
    await rendu();
  } catch (erreur) {
    if (jeton === renduEnCours) {
      rendre(`<h2>Erreur</h2><pre class="verdict">${escape(String(erreur))}</pre>`);
    }
  }
  // A newer section may have been chosen while this view was loading: repaint
  // the one actually selected, never leave the menu and the content in
  // disagreement.
  if (jeton !== renduEnCours) await afficher(sectionCourante);
}

/* Replayable demo: #demo=N puts the portal in state N of the video script. */
async function jouer(etape) {
  // The scripted flow switches role exactly as the portal now requires: the
  // DPO validates, then the MSP launches.
  if (etape >= 1) { element("jeton").value = "jeton-demo-dpo"; await enregistrerConformite(); }
  if (etape >= 2) {
    if (STATIQUE !== null) { etatLocal.lance = true; }
    else { element("jeton").value = "jeton-demo-msp"; await lancer(); }
  }
  if (etape === 3) { await afficher("nonattribution"); await demanderMesure(true); }
  if (etape === 4) { await afficher("nonattribution"); await demanderMesure(false); }
  if (etape === 5) await afficher("reference");
  if (etape === 6) await afficher("vagues");
  if (etape === 7) await afficher("deconseilles");
  if (etape === 8) await afficher("rapports");
  if (etape <= 2) await afficher("mesure");
}

function etape_demandee() {
  const brut = (location.hash || "").replace(/^#/, "");
  if (!brut) return -1;
  const params = new URLSearchParams(brut);
  const demo = params.get("demo");
  const section = params.get("s");
  if (demo !== null) return parseInt(demo, 10);
  if (section) { sectionCourante = section; return -2; }
  return -1;
}

async function chargerStatique(corpus) {
  const nom = corpus === "reel" ? "data/api-reel.json" : "data/api.json";
  try {
    STATIQUE = await (await fetch(nom)).json();
  } catch (erreur) {
    STATIQUE = {};
  }
  const meta = STATIQUE.META || {};
  CONFIG = {
    corpus: meta.corpus || corpus,
    campagne: meta.campagne || CONFIG.campagne,
    processus: meta.processus || CONFIG.processus,
    titre: meta.titre || CONFIG.titre,
  };
}

async function basculerCorpus(corpus) {
  if (STATIQUE === null) {
    element("mode").textContent =
      "mode live : l'API sert un seul corpus ; le corpus reel est dans le mode statique";
    return;
  }
  await chargerStatique(corpus);
  etatLocal = { conforme: false, lance: false, suspendu: false };
  element("mode").textContent =
    `mode statique : figures pre-calculees - ${CONFIG.titre}`;
  await majClient();
  await majEtat();
  await majNav();
  await afficher(sectionCourante);
}

async function majClient() {
  const { corps } = await api("/api/campagne");
  if (!corps.ok) return;
  const d = corps.donnees;
  element("client").textContent =
    `${d.id} - ${d.services.join(", ")} - fenetre ${d.fenetre} - graine ${d.graine}`;
}

async function demarrer() {
  const demande = new URLSearchParams(location.search).get("corpus");
  const selecteur = element("corpus");
  if (selecteur && (demande === "reel" || demande === "demo")) selecteur.value = demande;
  try {
    const sonde = await fetch("/api/health", {
      headers: { Authorization: `Bearer ${JETON()}` },
    });
    if (!sonde.ok) throw new Error("api indisponible");
    const sante = await sonde.json();
    // The live API serves ONE corpus: the portal must show the one it is
    // really serving, not the default of the selector.
    const corpus = sante.donnees && sante.donnees.corpus;
    if (corpus === "reel" || corpus === "demo") {
      CONFIG.corpus = corpus;
      CONFIG.campagne = sante.donnees.campagne || CONFIG.campagne;
      CONFIG.titre = corpus === "reel"
        ? "Corpus reel (Apache Kafka)" : "Demo synthetique";
    }
  } catch (erreur) {
    await chargerStatique(selecteur ? selecteur.value : "demo");
  }
  if (selecteur) {
    selecteur.value = CONFIG.corpus;
    // In live mode the API serves ONE corpus: the selector would lie.
    if (STATIQUE === null) {
      selecteur.disabled = true;
      selecteur.title = "mode live : l'API sert un seul corpus";
    }
  }
  element("mode").textContent = STATIQUE === null
    ? `mode live : API JSON - ${CONFIG.titre}`
    : `mode statique : figures pre-calculees - ${CONFIG.titre}`;
  await majClient();
  document.querySelectorAll(".nav button").forEach((bouton) =>
    bouton.addEventListener("click", () => afficher(bouton.dataset.section)));
  await majEtat();
  await majNav();
  const etape = etape_demandee();
  if (etape >= 0) await jouer(etape);
  else await afficher(sectionCourante);
}

document.addEventListener("DOMContentLoaded", () => {
  element("jeton").addEventListener("change", () => majEtat().then(() => afficher(sectionCourante)));
  const selecteur = element("corpus");
  if (selecteur) {
    selecteur.addEventListener("change", () => basculerCorpus(selecteur.value));
  }
  demarrer();
});
