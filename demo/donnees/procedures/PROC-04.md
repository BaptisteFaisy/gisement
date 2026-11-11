# Approvisionnement fournisseurs

> SYNTHETIQUE - DEMONSTRATION
>
> Procédure écrite du client fictif « Demo Distribution SAS ». Ce document fait
> partie du jeu de démonstration : il décrit le processus **déclaré**, que la
> mesure vient comparer au processus **réel** (chapitre 9.1 du cahier des
> charges). L'écart constaté est publié dans le rapport, jamais masqué.

**Référence** : PROC-04
**Processus concernés** : P-07, P-16, P-06, P-20
**Version** : 3.1 du 12 janvier 2024 (non révisée depuis)

## Objet

Le fournisseur transmet sa commande via le portail EDI, ou il la saisit directement. La commande est alors integree a l'ERP sans aucune ressaisie. Aucun tableur local n'est utilise pour le suivi des commandes fournisseurs.

## Modalités

1. Le déclencheur est la réception de la demande dans le système déclaré.
2. Le traitement est réalisé par le service concerné, sans délai maximal fixé.
3. La trace de l'opération est conservée dans l'outil de gestion.
4. Les exceptions sont remontées au responsable de service.

## Note de la mesure

L'observation des cinq canaux sur la fenêtre de six mois montre un fonctionnement
différent de celui décrit ci-dessus. Écart relevé par la mesure : **oui**.

78 % des commandes arrivent par courriel, sont recopiees dans un tableur de suivi local, puis ressaisies dans l'ERP. Le portail EDI existe et n'est pas utilise.
