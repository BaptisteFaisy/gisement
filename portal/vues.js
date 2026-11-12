/* Gisement - the twenty sections of the portal, one renderer per feature.
 *
 * Every renderer only formats what the API returns: no figure is computed here,
 * exactly as in the reports (21.5). A section that needs the measurement says so
 * instead of showing zeros.
 */

function ligne(nom, detail, classe = "") {
  return `<div class="ligne ${classe}"><span class="nom">${nom}</span>` +
    `<span class="detail">${detail ?? ""}</span></div>`;
}

function tableau(entetes, lignes) {
  const tete = entetes.map((h) => `<th>${escape(h)}</th>`).join("");
  const corps = lignes
    .map((l) => `<tr>${l.map((c) => `<td>${c ?? ""}</td>`).join("")}</tr>`)
    .join("");
  return `<table><thead><tr>${tete}</tr></thead><tbody>${corps}</tbody></table>`;
}

function titre(texte, sous) {
  return `<h2>${escape(texte)}</h2>` + (sous ? `<p class="note">${sous}</p>` : "");
}

function mesureRequise() {
  if (STATIQUE !== null || etatLocal.lance) return false;
  const lance = document.querySelector('[data-bouton="lancer"]');
  return !(lance && !lance.disabled) && !window.__lance;
}

async function donnees(chemin) {
  const { statut, corps } = await api(chemin);
  if (!corps.ok) return { erreur: corps.erreur || `HTTP ${statut}`, statut };
  return { d: corps.donnees, statut };
}

/* --------------------------------------------------------------- 1 conformite */

async function vueConformite() {
  const { corps } = await api("/api/health");
  const d = corps.donnees || {};
  rendre(
    titre("1. Perimetre et conformite",
      "Rien ne demarre sans la validation du DPO et des representants du personnel (EF-02, EF-04).") +
    `<p id="etat-campagne"></p>` +
    ligne("Validation DPO / representants", d.conformite_validee
      ? "<strong>enregistree</strong>" : "<strong class='refus'>non enregistree</strong>") +
    ligne("Etat de la campagne", escape(d.statut_campagne)) +
    ligne("Mesure", d.mesure_lancee ? "faite" : "non lancee") +
    ligne("Seuil d'agregation", "k &ge; 5 individus, jamais abaisse") +
    `<div class="actions">
       <button data-action="conformite">Enregistrer la validation DPO</button>
       <button data-bouton="lancer" data-action="lancer" disabled>Lancer la mesure</button>
       <button data-bouton="suspendre" data-action="suspendre" disabled>Suspendre</button>
       <button data-bouton="reprendre" data-action="reprendre" disabled>Reprendre</button>
     </div>
     <p class="note">Sans validation enregistree, le bouton <em>Lancer</em> reste grise et
       aucune ingestion n'a lieu : le refus est explicite (R1). La suspension est immediate,
       l'etat est conserve pour reprise (ENF-12).</p>`
  );
  await majEtat();
}

/* ------------------------------------------------------------------- 2 mesure */

async function vueMesure() {
  const { d, erreur } = await donnees("/api/campagnes/courante");
  if (erreur) return rendre(titre("2. Ingestion et assainissement") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("2. Ingestion et assainissement",
      "Cinq canaux, pseudonymises a l'ingestion avant tout modele (R3), categories sensibles " +
      "supprimees avant stockage (R4).") +
    ligne("Activites mesurees", `<strong>${d.activites}</strong>`) +
    ligne("Empreintes deterministes", `${d.groupes} groupes - un appel de modele par groupe, ` +
      `pas par activite (annexe G.1)`) +
    ligne("Motifs reconnus", `${d.motifs} dont ${d.revue_humaine} en revue humaine`) +
    ligne("Gisement net annuel", `<strong>${d.gisement_net_annuel} EUR</strong>`) +
    ligne("Cout mesure de la campagne", `${d.cout_mesure_usd} USD (annexe G : ~19,77 USD)`) +
    `<p class="note">Les transcriptions d'appels et les extractions de documents sont figees
      dans le depot : aucun appel a Amazon Transcribe ni a Bedrock Data Automation pendant le
      developpement, ils font 94 % du cout (regle 1 du 26.4).</p>`
  );
  window.__lance = true;
}

/* --------------------------------------------------------------- 3 couverture */

async function vueCouverture() {
  const { d, erreur } = await donnees("/api/campagnes/courante");
  if (erreur) return rendre(titre("3. Couverture publiee") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("3. La couverture est publiee, jamais implicite",
      "Un rapport qui ne publie pas sa couverture ment par omission (10.3).") +
    `<p class="etat"><strong>${escape(d.couverture)}</strong></p>` +
    (d.couverture_par_canal || []).map((c) => ligne(escape(c.split(" : ")[0]), escape(c.split(" : ")[1] || ""))).join("")
  );
}

/* ------------------------------------------------------------------ 4 motifs */

async function vueMotifs() {
  const { d, erreur } = await donnees("/api/motifs");
  if (erreur) return rendre(titre("4. Empreintes et motifs") + `<p class="refus">${escape(erreur)}</p>`);
  const cat = await donnees("/api/catalogue");
  const lignes = d.motifs.slice(0, 25).map((m) => [
    escape(m.ref), escape(m.nom.slice(0, 44)), m.occurrences_medianes,
    m.duree_minutes, escape(m.repartition), m.confiance,
    m.nouveau ? "<span class='refus'>nouveau</span>" : "",
    m.en_revue_humaine ? "a revoir" : "",
  ]);
  rendre(
    titre("4. Empreintes deterministes puis etiquetage par motif",
      `${d.nb_activites} activites reduites a ${d.nb_groupes} groupes : facteur ${d.facteur_reduction}. ` +
      `Le modele est appele une fois par groupe (21.2).`) +
    ligne("Motifs du catalogue reconnus", d.nb_motifs_catalogues) +
    ligne("Motifs nouveaux proposes", `${d.nb_nouveaux} (EF-21 - a valider par un humain)`) +
    ligne("En revue humaine", `${d.nb_en_revue} sous le seuil de confiance 0,70`) +
    ligne("Catalogue", cat.d ? `${cat.d.nb_motifs} motifs en donnees, ` +
      `${Object.keys(cat.d.familles).length} familles (annexe B)` : "") +
    tableau(["ref", "motif", "occ/mois", "min", "repartition", "confiance", "", ""], lignes) +
    `<details><summary>Revue humaine (${d.revue_humaine.length})</summary><pre class="verdict">` +
    d.revue_humaine.slice(0, 12).map((r) => `${r.objet} : ${r.raison}`).join("\n") +
    `</pre></details>`
  );
}

/* --------------------------------------------------------------- 5 processus */

async function vueProcessus() {
  const { d, erreur } = await donnees("/api/processus");
  if (erreur) return rendre(titre("5. Les processus") + `<p class="refus">${escape(erreur)}</p>`);
  const lignes = d.processus.map((p) => [
    `<a href="#s=processus" data-pid="${p.id}" class="pid">${p.id}</a>`,
    escape(p.nom.slice(0, 46)), escape(p.service),
    p.occurrences_medianes, p.duree_minutes,
    p.temps_net, p.gain_mensuel, p.ecart_naif, p.delai_retour_mois,
    p.type, escape(p.vague),
    p.origine === "declaree" ? "<span class='note'>declare</span>" : "",
  ]);
  rendre(
    titre("5. Les 23 processus du perimetre",
      "Volumes mesures sur les cinq canaux, mediane mensuelle (jamais la moyenne), amplitude " +
      "saisonniere publiee. Cliquez sur un identifiant pour la fiche complete.") +
    tableau(["id", "processus", "service", "occ/mois", "min", "h nettes", "EUR/mois",
             "x naif", "retour", "type", "vague", ""], lignes)
  );
  document.querySelectorAll("a.pid").forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); voirFiche(a.dataset.pid); }));
}

/* ------------------------------------------------------------------- 6 fiche */

async function voirFiche(pid) {
  const { d, erreur } = await donnees(`/api/processus/${pid}`);
  if (erreur) return rendre(titre(`6. Fiche ${pid}`) + `<p class="refus">${escape(erreur)}</p>`);
  const v = d.volume, c = d.calcul, f = d.faisabilite, r = d.recommandation;
  const ecart = d.travail_reel_vs_procedure.ecart;
  rendre(
    titre(`6. Fiche processus ${d.id} - ${escape(d.nom)}`,
      `Service ${escape(d.service)} &middot; canaux ${d.canaux.join(", ")} &middot; ` +
      `mesure ${v.origine === "declaree" ? "declaree en entretien (invisible dans les canaux)" : "mesuree sur les canaux"}`) +
    `<h3>Volume mesure</h3>` +
    ligne("Occurrences medianes", `${v.occurrences_medianes} / mois ${escape(v.amplitude_saisonnieres)} (saisonnalite)`) +
    ligne("Serie mensuelle", v.serie_mensuelle.join(", ")) +
    ligne("Duree unitaire", `${v.duree_unitaire_minutes} min (${v.duree_statut}, ${v.duree_mesuree_sur} cas)`) +
    ligne("Repartition", escape(v.repartition)) +
    ligne("Part de cas atypiques", v.part_atypique) +
    `<h3>Travail reel vs procedure ecrite</h3>` +
    (ecart
      ? ligne(`Procedure ${escape(d.travail_reel_vs_procedure.procedure_ref)}`,
          ecart.majeur ? "<strong class='refus'>ecart majeur</strong>" : "ecart mineur") +
        `<p class="note">Declare : ${escape(ecart.declare.slice(0, 220))}</p>` +
        `<p class="note">Observe : ${escape(ecart.observe.slice(0, 220))}</p>` +
        ligne("Part de pratique divergente", ecart.part_pratique_divergente)
      : ligne("Aucune procedure ecrite comparee", "")) +
    `<h3>Calcul du gisement</h3>` +
    ligne("Temps brut", `${c.temps_brut} h/mois`) +
    ligne("Correction fragmentation", `x ${c.coefficient_fragmentation} -> ${c.temps_fragmente} h/mois`) +
    ligne("Correction transfert", `- ${c.temps_transfere} h/mois ` +
      `(${c.detail_transfert.map((t) => `${t[0]} ${t[1]}`).join(", ") || "aucun : etape supprimee"})`) +
    ligne("Correction ineliminable", `- ${c.temps_ineliminable} h/mois`) +
    ligne("<strong>Temps net</strong>", `<strong>${c.temps_net} h/mois</strong> ` +
      `[${c.intervalle_net[0]} - ${c.intervalle_net[1]}] a 90 % (${c.tirages_monte_carlo} tirages, graine fixee)`) +
    ligne("Gain mensuel", `${c.gain_mensuel} EUR ` +
      `[${c.gain_mensuel_intervalle ? c.gain_mensuel_intervalle[0] + " - " + c.gain_mensuel_intervalle[1] : "-"}]`) +
    ligne("Gain annuel", `${c.gain_annuel} EUR`) +
    ligne("Ecart au calcul naif", `<strong>x ${c.ecart_naif}</strong> ` +
      `(naif ${c.gain_naif_mensuel} EUR/mois, retour ${c.delai_retour_naif_mois} mois ` +
      `contre ${c.delai_retour_mois} mois reels)`) +
    ligne("Cout annee 1", `${c.cout.annee_1} EUR (dev ${c.cout.developpement}, ` +
      `outil ${c.cout.outil_annuel}, maintenance ${c.cout.maintenance})`) +
    ligne("Gain sur 3 ans", `${c.gain_trois_ans} EUR`) +
    `<h3>Faisabilite</h3>` +
    ligne("Type recommande", `<strong>${f.type || "?"}</strong> ${escape((f.motifs_decision || [])[0] || "")}`) +
    ligne("Criteres", `API ${f.api_existe ? "oui" : "non"} &middot; interface stable ` +
      `${f.interface_stable ? "oui" : "non"} &middot; jugement ${f.jugement_requis ? "requis" : "non requis"}`) +
    ligne("Risque / score", `${escape(f.risque || "")} &middot; score de priorite ${f.score_priorite || ""} ` +
      `(gain ${f.criteres?.gain}, faisabilite ${f.criteres?.faisabilite}, rapidite ${f.criteres?.rapidite}, ` +
      `visibilite ${f.criteres?.visibilite}, juridique ${f.criteres?.securite_juridique})`) +
    ligne("Portee du projet", `${f.part_volume_traitee || "1"} du volume` +
      (f.suppression_etape ? " - <strong>etape supprimee</strong>, pas de transfert ni d'ineliminable" : "")) +
    `<h3>Recommandation</h3>` +
    (r.deconseille
      ? ligne("<strong class='refus'>Ne pas automatiser</strong>",
          `${escape(r.deconseille)} - ${escape(r.seuil_atteint)}`) +
        ligne("Condition de reexamen", escape(r.condition_reexamen))
      : ligne("Vague", `${escape(r.vague)}${r.rang ? ", projet " + r.rang : ""} - ` +
          `${r.gain_mensuel} EUR/mois pour ${r.cout_annee_1} EUR, retour ${r.retour_mois} mois`)) +
    `<h3>Confidentialite</h3><p class="note">${escape(d.confidentialite)}</p>` +
    `<p><a href="#s=processus" id="retour-processus">&larr; tous les processus</a></p>`
  );
  element("retour-processus")?.addEventListener("click", (e) => {
    e.preventDefault(); afficher("processus");
  });
}

async function vueFiche() {
  await voirFiche(CONFIG.processus);
}

/* --------------------------------------------------------------- 7 reference */

async function vueReference() {
  const { d, erreur } = await donnees(`/api/gisements/${CONFIG.processus}`);
  if (erreur) return rendre(titre("7. Le facteur de surestimation") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("7. Le chiffre qui emporte l'adhesion d'un juge metier",
      `Le processus le plus mesure (${CONFIG.processus}) : le calcul naif contre ` +
      "le calcul reel, avec les quatre corrections (annexe A).") +
    tableau(["", "Calcul naif", "Gisement"], [
      ["Gain mensuel", `${d.gain_naif_mensuel} EUR`, `<strong>${d.gain_mensuel} EUR</strong>`],
      ["Temps mensuel", `${d.temps_brut} h`, `<strong>${d.temps_net} h nettes</strong> ` +
        `[${d.intervalle[0]} - ${d.intervalle[1]}]`],
      ["Delai de retour", `${d.delai_retour_naif_mois} mois`, `<strong>${d.delai_retour_mois} mois</strong>`],
      ["Facteur de surestimation", "-", `<strong class="refus">x ${d.ecart_naif}</strong>`],
    ]) +
    `<p class="note">Un client qui signe sur ${d.delai_retour_naif_mois} mois et decouvre
      ${d.delai_retour_mois} mois ne rachete jamais - et il le dit a ses pairs. C'est ce tableau,
      imprime pour chaque processus, qui rend le reste du rapport credible.</p>`
  );
}

/* ---------------------------------------------------------------- 8 backtest */

async function vueBacktest() {
  const { d, erreur } = await donnees("/api/backtest");
  if (erreur) return rendre(titre("8. Back-test") + `<p class="refus">${escape(erreur)}</p>`);
  const lignes = d.secteurs.map((s) => [
    escape(s.secteur), s.cas, s.min, `<strong>${s.median}</strong>`, s.max,
  ]);
  lignes.push(["<strong>TOTAL</strong>", `<strong>${d.cas_total}</strong>`,
    d.facteur_min_global, `<strong>${d.facteur_median_global}</strong>`, d.facteur_max_global]);
  rendre(
    titre("8. Le facteur est une distribution, pas une constante",
      "Un seul cas de reference est une anecdote. Le back-test le mesure sur quatre secteurs " +
      "(decision D-24). Le harnais casse si la mediane tombe sous " + d.seuil_de_rupture + ".") +
    tableau(["secteur", "cas", "min", "median", "max"], lignes) +
    ligne("La these tient", d.tient
      ? `<strong class="autorise">oui</strong> - mediane ${d.facteur_median_global}`
      : "<strong class='refus'>non</strong>") +
    `<p class="note">Les cas hors client de demo sont synthetiques, construits a partir de
      l'experience MSP : c'est un filet de non-regression sur la distribution, pas un audit
      independant. L'audit independant, c'est la base realise-contre-predit du suivi trimestriel.</p>`
  );
}

/* ------------------------------------------------------------------ 9 vagues */

async function vueVagues() {
  const { d, erreur } = await donnees("/api/projets");
  if (erreur) return rendre(titre("9. La sequence") + `<p class="refus">${escape(erreur)}</p>`);
  const titres = {
    vague_1: "Vague 1 - amorcage (rapide, visible, sur)",
    vague_2: "Vague 2 - structurel",
    vague_3: "Vague 3 - transformation",
    aucune: "Reserve - classes, hors vagues (capacite saturee)",
  };
  let html = titre("9. La sequence, pas un classement par gain",
    "Classer par gain decreissant envoie le client sur le projet le plus gros, donc le plus " +
    "risque : un echec initial tue le programme pour des annees (15.1).") +
    ligne("Part de processus deconseilles", `${d.part_deconseilles} (bande saine 15 a 30 %, KPI-9)`);
  for (const vague of ["vague_1", "vague_2", "vague_3", "aucune"]) {
    const projets = d.projets.filter((p) => p.vague === vague);
    if (!projets.length) continue;
    html += `<h3>${titres[vague]}</h3>` + projets.map((p) => ligne(
      `${p.rang ? p.rang + ". " : ""}${p.processus_id} [type ${p.type}]`,
      `${p.gain_mensuel} EUR/mois &middot; retour ${p.delai_retour_mois} mois &middot; ` +
      `risque ${escape(p.risque)} &middot; score ${p.score}`
    )).join("");
  }
  if (!d.vague1_existe) {
    html += `<p class="refus">${escape(d.recommandation_elargissement)}</p>`;
  } else {
    html += `<p class="note">EF-43 verifie : la vague 1 existe, elle contient au moins un projet
      a retour &lt; 6 mois, et elle ne contient <strong>pas</strong> le plus gros gain du
      portefeuille (R17).</p>`;
  }
  rendre(html);
}

/* -------------------------------------------------------------------- 10 plan */

async function vuePlan() {
  const { d, erreur } = await donnees("/api/plan");
  if (erreur) return rendre(titre("10. Le plan") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("10. Une sequence n'est pas un planning",
      `Le MSP n'a que ${d.capacite.consultants} consultant(s) x ${d.capacite.jours_par_mois} jours ` +
      `par mois, et certains projets doivent attendre les autres.`) +
    ligne("Capacite mensuelle", `${d.capacite.jours_disponibles} jours`) +
    ligne("Duree totale", `${d.duree_totale_mois} mois`) +
    ligne("Capacite utilisee", d.capacite_utilisee) +
    ligne("Gain annuel cumule des taches planifiees", `${d.gain_cumule} EUR`) +
    ligne("Chemin critique", d.chemin_critique.join(" &rarr; ") || "-") +
    `<h3>Dependances</h3>` +
    d.dependances.map((dep) => ligne(
      `${dep.projet} attend ${dep.apres.join(", ")}`, escape(dep.raison)
    )).join("") +
    `<h3>Gantt</h3><pre class="verdict">${escape(d.gantt)}</pre>` +
    `<h3>Non planifiables</h3>` +
    (d.impossibles.length
      ? d.impossibles.map((i) => ligne(i.projet, escape(i.raison))).join("")
      : `<p class="note">Aucun.</p>`)
  );
}

/* ------------------------------------------------------------ 11 deconseilles */

async function vueDecconseilles() {
  const { d, erreur } = await donnees("/api/deconseilles");
  if (erreur) return rendre(titre("11. A ne pas automatiser") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("11. Ce qui ne doit PAS etre automatise",
      "Un outil qui trouve toujours quelque chose a automatiser est un outil de vente, pas un " +
      "instrument. Dire non est ce qui rend le oui credible (chapitre 16).") +
    d.map((x) => ligne(
      `<strong>${x.processus_id}</strong> - ${escape(x.motif)}`,
      `${escape(x.seuil_atteint)}<br><span class="note">${escape(x.condition_reexamen)}</span>`
    )).join("") +
    `<p class="note">Chaque deconseil porte sa <strong>condition de reexamen</strong> : un "non"
      est publie comme un "pas encore", ce qui donne au suivi trimestriel une raison d'exister.</p>`
  );
}

/* ------------------------------------------------------------------ 12 suivi */

async function vueSuivi() {
  const { d, erreur } = await donnees("/api/suivi");
  if (erreur) return rendre(titre("12. Suivi") + `<p class="refus">${escape(erreur)}</p>`);
  const p = d.precision_cumulee;
  rendre(
    titre("12. Le realise contre le predit",
      "C'est ce qui declenche la deuxieme vente, et c'est l'actif que personne ne peut copier : " +
      "au bout de huit trimestres, la base de realise devient une reference (8.2, KPI-6).") +
    ligne("Trimestres suivis", `${p.nb_trimestres} sur ${d.suivis.length / Math.max(1, p.nb_projets) | 0}`) +
    ligne("Projets suivis", p.nb_projets) +
    ligne("Ecart moyen", `<strong>${p.ecart_moyen}</strong> (cible ${escape(p.cible)})`) +
    ligne("Part de predictions conformes", p.part_conformes) +
    ligne("Part de predictions invalides", p.part_invalides) +
    ligne("Alertes", escape(d.resume_alertes)) +
    `<h3>Detail par trimestre</h3>` +
    tableau(["projet", "trimestre", "predit", "realise", "ecart", "statut", "parametre fautif"],
      d.suivis.map((s) => [s.projet, s.trimestre, s.predit, s.mesure, s.ecart,
        `<span class="${s.statut === "conforme" ? "autorise" : s.statut === "prediction_invalide" ? "refus" : ""}">${s.statut}</span>`,
        escape(s.parametre_fautif)])) +
    `<h3>Alertes</h3>` +
    (d.alertes.length ? d.alertes.map((a) => ligne(
      `<span class="${a.gravite === "critique" ? "refus" : ""}">${a.gravite}</span> ${a.projet} - ${a.code}`,
      escape(a.message))).join("") : `<p class="note">Aucune alerte.</p>`) +
    `<h3>Coefficients recalibres par l'historique</h3>` +
    d.coefficients_calibres.map((c) => ligne(
      `${escape(c.nom)} : ${c.defaut} &rarr; <strong>${c.calibre}</strong>`,
      escape(c.commentaire))).join("") +
    `<p class="note">${escape(d.note)}</p>`
  );
}

/* --------------------------------------------------------- 13 non-attribution */

async function vueNonattribution() {
  rendre(
    titre("13. Aucune attribution individuelle - impose par la passerelle",
      "La regle n'est pas une consigne dans une invite : elle est evaluee avant l'outil, sur des " +
      "faits structures (R5). Un agent qui essaie recoit un refus qui nomme la regle.") +
    `<div class="actions">
       <button data-action="mesure-individuelle" class="danger">Demander une mesure par salarie</button>
       <button data-action="mesure-agregee" class="secondary">Demander une mesure agreggee (service)</button>
       <button data-action="mesure-filtres" class="danger">Isoler par combinaison de filtres</button>
     </div>
     <pre id="verdict" class="verdict">Cliquez sur un bouton : la passerelle repond.</pre>
     <p class="note">Les 50 requetes du harnais (dont 18 par combinaison de filtres) sont toutes
       refusees : c'est le seul critere <strong>bloquant</strong> de la recette - un seul echec
       interdit la soumission (R7).</p>`
  );
}

async function mesureParFiltres() {
  const { statut, corps } = await api("/api/mesure", {
    method: "POST",
    body: JSON.stringify({
      canal: "tickets", groupements: ["service", "motif"],
      filtres: { service: "comptabilite", site: "lyon", motif: "RESS-01" },
      taille_groupe: 3, taille_resultat_apres_filtres: 3,
    }),
  });
  const cible = element("verdict");
  cible.className = corps.ok ? "verdict autorise" : "verdict refus";
  cible.textContent = corps.ok
    ? `AUTORISE (${statut})`
    : `REFUSE (${statut}) - regles violees : ${(corps.regles_violees || []).join(", ")}\n${corps.erreur}`;
}

/* ----------------------------------------------------------------- 14 privacy */

async function vuePrivacy() {
  const { d, erreur } = await donnees("/api/privacy");
  if (erreur) return rendre(titre("14. Privacy") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("14. Au-dela du k &ge; 5 : bruit differentiel et preuves verifiables",
      "k &ge; 5 arrete la re-identification directe, pas l'inférence sur un agrégat. Le bruit " +
      "de Laplace est opt-in : un rapport de direction garde les chiffres exacts.") +
    ligne("Garanties", escape(d.resume_garanties)) +
    ligne("Epsilon / delta", `${d.epsilon} / ${d.delta}`) +
    ligne("Seuil de revelation", `${d.seuil_revelation} de l'agrege par individu`) +
    ligne("Agrege exact", `${d.agregat_exact_heures} h`) +
    ligne("Agrege publie avec bruit", `${d.agregat_bruite_heures} h (ecart ${d.ecart_absolu})`) +
    `<h3>Certificats de non-attribution</h3>` +
    `<p class="note">Chaque certificat prouve que le seuil a ete respecte <strong>sans publier la
      taille du groupe</strong>. Il est chainé par empreinte : falsifier un champ, un seuil ou une
      date casse la verification.</p>` +
    tableau(["mesure", "seuil", "conforme", "regles", "empreinte", "attestation"],
      d.preuves.slice(0, 8).map((p) => [
        p.mesure, p.seuil, p.conforme ? "<span class='autorise'>oui</span>" : "<span class='refus'>non</span>",
        p.regles.join(", "), p.empreinte, escape(p.attestation.slice(0, 90)) + "…"])) +
    ligne("Chaine verifiee", d.chaine_verifiee
      ? "<strong class='autorise'>oui</strong>" : `<strong class='refus'>non</strong> ${d.erreurs_chaine.join("; ")}`)
  );
}

/* ------------------------------------------------------------------- 15 cedar */

async function vueCedar() {
  const { d, erreur } = await donnees("/api/cedar");
  if (erreur) return rendre(titre("15. Politique Cedar") + `<p class="refus">${escape(erreur)}</p>`);
  const conf = d.configuration_passerelle;
  rendre(
    titre("15. La politique deployee sur AgentCore Gateway",
      "Point 5 du chapitre 34 resolu (D-22) : le refus k &ge; 5 est un <code>forbid</code> Cedar " +
      "evalue par la passerelle, et ce que Cedar ne sait pas exprimer est refuse par un " +
      "intercepteur REQUEST Lambda, avant l'appel a la cible.") +
    ligne("Interdictions Cedar", d.interdictions) +
    ligne("Autorisations", `${d.autorisations} (les cinq roles du chapitre 7)`) +
    ligne("Verification structurelle", d.verification.length
      ? `<span class="refus">${d.verification.join("; ")}</span>` : "<span class='autorise'>OK</span>") +
    ligne("Passerelle", `${conf.protocolType} / ${conf.authorizerType} / ` +
      `moteur de politiques ${conf.policyEngineConfiguration.mode}`) +
    ligne("Intercepteur", `${conf.interceptorConfigurations[0].interceptionPoints.join(",")} - ` +
      `entetes transmis : ${conf.interceptorConfigurations[0].inputConfiguration.passRequestHeaders} ` +
      `(le tenant vient du jeton, EF-71)`) +
    `<p class="note">${escape(d.note)}</p>` +
    `<details open><summary>Politique Cedar generee (${d.lignes} lignes)</summary>` +
    `<pre class="verdict">${escape(d.cedar)}</pre></details>`
  );
}

/* ------------------------------------------------------------------ 16 qualite */

async function vueQualite() {
  const { d, erreur } = await donnees("/api/evaluation");
  if (erreur) return rendre(titre("16. Qualite") + `<p class="refus">${escape(erreur)}</p>`);
  const c = d.classification, r = d.rappel_motifs, e = d.calcul_economique, b = d.backtest;
  rendre(
    titre("16. La qualite est mesuree, pas promise (chapitre 27)",
      "Les quatre mesures tournent dans le harnais <code>gisement eval</code> et en CI.") +
    ligne("Precision de classification",
      `${c.accords}/${c.total} = <strong>${c.taux}</strong> (seuil ${c.seuil}) ` +
      (c.tient ? "<span class='autorise'>OK</span>" : "<span class='refus'>ECHEC</span>")) +
    ligne("Rappel des motifs implantes",
      `${r.reconnus}/${r.total} = <strong>${r.taux}</strong> (seuil ${r.seuil}) ` +
      (r.tient ? "<span class='autorise'>OK</span>" : "<span class='refus'>ECHEC</span>")) +
    ligne("Precision du calcul economique",
      `${e.accords}/${e.total} = <strong>${e.taux}</strong> - le calcul est deterministe, ` +
      `l'accord est total`) +
    ligne("Back-test du facteur",
      `${b.cas_total} cas, ${b.secteurs.length} secteurs, mediane <strong>${b.facteur_median_global}</strong> ` +
      `(rupture sous ${b.seuil_de_rupture})`) +
    ligne("Non-attribution", "50 requetes, 50 refus - <strong>bloquant</strong> (R7)")
  );
}

/* --------------------------------------------------------------------- 17 cout */

async function vueCout() {
  const { d, erreur } = await donnees("/api/cout");
  if (erreur) return rendre(titre("17. Cout") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("17. Le cout est mesure, jamais estime a posteriori",
      "ENF-10, KPI-8, R24 : l'ecart a l'estimation de l'annexe G doit rester sous 25 %.") +
    ligne("Cout mesure de la cartographie", `<strong>${d.cout_mesure_usd} USD</strong>`) +
    ligne("Amazon Transcribe", `${d.transcribe.minutes} min -> ${d.transcribe.usd} USD`) +
    ligne("Bedrock Data Automation", `${d.data_automation.pages} pages -> ${d.data_automation.usd} USD`) +
    ligne("Inference Bedrock", `${d.inference.appels} appels, ${d.inference.jetons_entree} jetons ` +
      `en entree -> ${d.inference.usd} USD`) +
    ligne("Repartition", `Transcribe ${d.repartition.transcribe} &middot; ` +
      `Data Automation ${d.repartition.data_automation} &middot; inference ${d.repartition.inference}`) +
    ligne("Estimation annexe G", `${d.estimation_annexe_g_usd} USD`) +
    ligne("Ecart", `<strong>${d.ecart_a_l_estimation}</strong> (cible &lt; 0,25)`) +
    ligne("Cartographies financees par les credits",
      `${d.cartographies_financees} avec ${d.budget_credits_usd} USD`)
  );
}

/* -------------------------------------------------------------- 18 connecteurs */

async function vueConnecteurs() {
  const { d, erreur } = await donnees("/api/connecteurs");
  if (erreur) return rendre(titre("18. Connecteurs") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("18. Brancher les vrais outils du client",
      "Le jeu de demo est synthetique ; un client reel a deja des outils. Le client HTTP est " +
      "injecte, donc aucune requete reseau en CI.") +
    `<h3>Jira &rarr; canal tickets</h3><pre class="verdict">${escape(JSON.stringify(d.jira.exemple, null, 2))}</pre>` +
    `<h3>ServiceNow &rarr; canal tickets</h3><pre class="verdict">${escape(JSON.stringify(d.servicenow.exemple, null, 2))}</pre>` +
    `<h3>Export ERP (Sage / Cegid / SAP) &rarr; canal journaux</h3>` +
    `<pre class="verdict">${escape(JSON.stringify(d.sage.exemple, null, 2))}</pre>` +
    `<p class="note">${escape(d.note)}</p>`
  );
}

/* ------------------------------------------------------------------ 19 rapports */

async function vueRapports() {
  rendre(
    titre("19. Les livrables",
      "Le rapport dirigeant tient en deux pages, le registre de conformite est ce que le DPO " +
      "presente a la CNIL, la proposition commerciale est ce que le MSP envoie pour signer.") +
    `<div class="actions">
       <button data-action="rapport-fr">Rapport dirigeant (FR)</button>
       <button data-action="rapport-en" class="secondary">Executive report (EN)</button>
       <button data-action="registre" class="secondary">Registre de conformite</button>
       <button data-action="proposition">Proposition commerciale</button>
     </div>
     <pre id="document" class="verdict">Choisissez un livrable.</pre>
     <p class="note">Le PDF est produit par un writer PDF 1.4 en bibliotheque standard, sans
       dependance : <code>python3 -m gisement.cli proposition --pdf proposition.pdf</code>.</p>`
  );
}

async function afficherDocument(chemin, clef) {
  const { corps } = await api(chemin);
  const cible = element("document");
  if (!cible) return;
  cible.className = "verdict";
  cible.textContent = corps.donnees
    ? (corps.donnees[clef] || JSON.stringify(corps.donnees, null, 2))
    : corps.erreur;
}

/* -------------------------------------------------------------------- 20 quick */

async function vueQuick() {
  const { d, erreur } = await donnees("/api/quick");
  if (erreur) return rendre(titre("20. Amazon Quick") + `<p class="refus">${escape(erreur)}</p>`);
  rendre(
    titre("20. Les tables publiees vers Amazon Quick",
      "Le tableau de bord et le rapport lisent les memes chiffres : ils ne peuvent pas diverger.") +
    `<h3>Vagues</h3>` +
    tableau(["vague", "projets", "cout total", "gain annuel", "processus"],
      d.vagues.map((v) => [escape(v.vague), v.nb_projets, v.cout_total, v.gain_annuel_total,
        v.processus.join(", ")])) +
    `<h3>Visuels du tableau de bord</h3>` +
    tableau(["id", "type", "dataset", "titre"],
      d.tableau_de_bord.visuels.map((v) => [v.id, v.type, v.dataset, escape(v.titre)])) +
    `<h3>Tendances (extrait)</h3>` +
    tableau(["processus", "service", "mediane", "amplitude", "serie mensuelle"],
      d.tendances.map((t) => [t.processus_id, escape(t.service), t.mediane,
        t.amplitude.join(" - "), t.occurrences_par_mois.join(", ")]))
  );
}

/* -------------------------------------------------------------------- registry */

const VUES = {
  conformite: vueConformite, mesure: vueMesure, couverture: vueCouverture, motifs: vueMotifs,
  processus: vueProcessus, fiche: vueFiche, reference: vueReference, backtest: vueBacktest,
  vagues: vueVagues, plan: vuePlan, deconseilles: vueDecconseilles, suivi: vueSuivi,
  nonattribution: vueNonattribution, privacy: vuePrivacy, cedar: vueCedar, qualite: vueQualite,
  cout: vueCout, connecteurs: vueConnecteurs, rapports: vueRapports, quick: vueQuick,
};

const ACTIONS = {
  conformite: enregistrerConformite,
  lancer: lancer,
  suspendre: suspendre,
  reprendre: reprendre,
  "mesure-individuelle": () => demanderMesure(true),
  "mesure-agregee": () => demanderMesure(false),
  "mesure-filtres": mesureParFiltres,
  "rapport-fr": () => afficherDocument(`/api/rapports/${CONFIG.campagne}?langue=fr`, "rapport"),
  "rapport-en": () => afficherDocument(`/api/rapports/${CONFIG.campagne}?langue=en`, "rapport"),
  registre: () => afficherDocument(`/api/registre-conformite/${CONFIG.campagne}?langue=fr`, "registre"),
  proposition: () => afficherDocument("/api/proposition", "texte"),
};

document.addEventListener("click", (evenement) => {
  const bouton = evenement.target.closest("[data-action]");
  if (!bouton) return;
  const action = ACTIONS[bouton.dataset.action];
  if (action) action();
});
