"""Coordination : délègue chaque contrôle, range chaque résultat, applique le § 10, conclut.

Seule à lire et à écrire l'état de la demande. Les agents ne s'appellent jamais entre eux.
Toute demande finit par une décision ou une escalade motivée : une borne atteinte ou une erreur
imprévue mène aussi à une escalade, jamais à un blocage silencieux.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from time import monotonic, perf_counter
from typing import Any

from .agents.antifraude import AvisFraude, evaluer_risque, partenaire_bouchon
from .agents.eligibilite import verifier_eligibilite
from .agents.estimation import estimer
from .agents.pieces import demander_complement, verifier_pieces
from .bornes import BORNES, Bornes
from .etat import EtatDemande
from .regles import continue_en_mode_degrade, depasse_seuil_delegation, jours_entre


class RegistreAppels:
    """Références déjà soumises au partenaire, pour un appel de traiter_demande ou traiter_lot.

    Contrat § 6 : un seul appel par dossier. Le verrou protège les demandes traitées en
    concurrence. Portée : une exécution ; au-delà (autre lot, redémarrage), non couvert.
    """

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._references: set[str] = set()

    def reserver(self, reference: str) -> bool:
        with self._verrou:
            if reference in self._references:
                return False
            self._references.add(reference)
            return True


def appel_unique(consulter: Callable[..., AvisFraude], registre: RegistreAppels) -> Callable[..., AvisFraude]:
    def proteger(**donnees: Any) -> AvisFraude:
        if not registre.reserver(donnees["reference"]):
            return AvisFraude(statut="indisponible", raison="appel_deja_effectue")
        return consulter(**donnees)
    return proteger


class _BorneAtteinte(Exception):
    def __init__(self, borne: str) -> None:
        super().__init__(borne)
        self.borne = borne


class _Parcours:
    def __init__(self, demande: dict[str, Any], bornes: Bornes, consulter: Callable[..., AvisFraude],
                 limite: float | None = None) -> None:
        self.etat = EtatDemande(demande)
        self.bornes = bornes
        self.consulter = consulter
        # une seule limite par demande : reçue de la lecture des pièces si elle a eu lieu, sinon posée ici
        self.limite = limite if limite is not None else monotonic() + bornes.duree_max_s - bornes.reserve_fiche_s

    def deleguer(self, agent: str, fonction: Callable[..., Any], **entrees: Any) -> Any:
        """Vérifie les bornes, appelle l'agent avec ses seules entrées, range son résultat."""
        if len(self.etat.trace) >= self.bornes.etapes_max - 1:  # la dernière étape reste à l'issue
            raise _BorneAtteinte("etapes_max")
        if monotonic() > self.limite:
            raise _BorneAtteinte("duree_max_s")
        debut = perf_counter()
        try:
            resultat = fonction(**entrees)
        except Exception:
            self.etat.noter_echec(agent, fonction.__name__, (perf_counter() - debut) * 1000)
            raise
        statut = "echec" if getattr(resultat, "statut", None) == "indisponible" else "ok"
        self.etat.ranger(agent, resultat, fonction.__name__, (perf_counter() - debut) * 1000, statut,
                         appel_externe=getattr(resultat, "appel_externe", False),
                         raison=getattr(resultat, "raison", None))  # un code court à nous, jamais le contenu reçu
        return resultat

    def consulter_dans_le_budget(self, **donnees: Any) -> AvisFraude:
        """Le partenaire reçoit le plus petit de ses 3 s et du temps restant à la demande (réserve de la fiche déduite).

        Trop peu de temps : aucun appel, l'avis est indisponible et le mode dégradé du § 9 s'applique. Ce cas n'arrive
        qu'à l'étape Anti-fraude, donc après Éligibilité, Pièces et Estimation : la règle des 1 500 € ne les saute jamais.
        """
        delai = min(self.bornes.delai_partenaire_s, self.limite - monotonic())
        if delai < self.bornes.delai_partenaire_min_s:
            return AvisFraude(statut="indisponible", raison="budget_epuise")
        return self.consulter(**donnees, delai_s=delai)

    def conclure(self, motif: str, *, decision: str | None = None, montant: float | None = None,
                 file: str | None = None, avis: dict[str, Any] | None = None,
                 mode_degrade: bool = False, arret: dict[str, str] | None = None) -> dict[str, Any]:
        """Écrit la section issue (dernière étape) et construit la fiche de décision (§ 11)."""
        issue = "decision" if decision else "escalade"
        self.etat.ranger("coordination", {"issue": issue, "motif": motif}, "conclure", 0.0)
        return {"reference": self.etat.demande["reference"], "issue": issue, "decision": decision,
                "montant_rembourse": montant, "motif": motif, "file": file, "avis_fraude": avis,
                "mode_degrade": mode_degrade, "trace": self.etat.trace, "arret": arret}

    def derouler(self) -> dict[str, Any]:
        demande = self.etat.demande
        contrat, sinistre = demande["contrat"], demande["sinistre"]

        # Données impossibles : un sinistre ne peut pas être déclaré avant d'être survenu. La spec (E4, « au plus tard
        # 30 jours après ») ne prévoit pas ce cas ; aucune règle n'est inventée, une personne reprend la demande.
        if jours_entre(sinistre["date_survenance"], sinistre["date_declaration"]) < 0:
            return self.conclure(f"Dates incohérentes : déclaration du {sinistre['date_declaration']} antérieure à la "
                                 f"survenance du {sinistre['date_survenance']} : reprise manuelle", file="gestionnaire")

        eligibilite = self.deleguer("eligibilite", verifier_eligibilite, contrat=contrat, sinistre=sinistre)
        if not eligibilite.eligible:  # règle 1 ; court-circuit : les pièces ne sont pas contrôlées
            return self.conclure("Non éligible : " + ", ".join(eligibilite.conditions_non_remplies),
                                 decision="refusee", montant=0.0)

        pieces = self.deleguer("pieces", verifier_pieces, type_sinistre=sinistre["type"],
                               pieces=demande["pieces"])
        depots = demande.get("espace_assure", {}).get("depots", [])
        for tentative in range(self.bornes.complements_max):
            if pieces.complet:
                break
            precedent = (pieces.manquantes, pieces.factures_lisibles)
            pieces = self.deleguer("pieces", demander_complement, type_sinistre=sinistre["type"],
                                   pieces=pieces.pieces, depots=depots, tentative=tentative)
            if pieces.sans_depot:  # § 5 : aucun dépôt du type demandé
                return self.conclure("Pièces manquantes, aucun dépôt de l'assuré : "
                                     + ", ".join(pieces.sans_depot), file="gestionnaire")
            if not pieces.complet and (pieces.manquantes, pieces.factures_lisibles) == precedent:
                raise _BorneAtteinte("etat_repete")
        if not pieces.complet:
            raise _BorneAtteinte("complements_max")

        estimation = self.deleguer("estimation", estimer, montant_declare=sinistre["montant_declare"],
                                   formule=contrat["formule"], factures_lisibles=pieces.factures_lisibles)
        if estimation.montant_estime == 0:  # règle 3
            return self.conclure("Dommage inférieur ou égal à la franchise", decision="refusee", montant=0.0)

        avis = self.deleguer("antifraude", evaluer_risque, reference=demande["reference"],
                             type_sinistre=sinistre["type"], date_survenance=sinistre["date_survenance"],
                             montant_declare=sinistre["montant_declare"],
                             date_souscription=contrat["date_souscription"],
                             sinistres_12_mois=demande["historique"]["sinistres_12_mois"],
                             code_postal=demande["assure"]["code_postal"],
                             montant_justifie=estimation.montant_justifie,
                             consulter=self.consulter_dans_le_budget)
        retenu, degrade = None, False
        if avis.statut == "avis":  # règle 4
            retenu = {"niveau": avis.niveau, "score": avis.score}
            if avis.niveau == "modere":
                return self.conclure("Avis anti-fraude modéré : contrôle renforcé", file="gestionnaire",
                                     avis=retenu)
            if avis.niveau == "eleve":
                return self.conclure("Avis anti-fraude élevé : suspicion de fraude",
                                     file="cellule_fraude", avis=retenu)
        elif avis.statut == "indisponible":  # règle 4, mode dégradé (§ 9)
            degrade = True
            if not continue_en_mode_degrade(estimation.montant_estime):
                return self.conclure("Avis anti-fraude indisponible : contrôle anti-fraude manuel",
                                     file="cellule_fraude", mode_degrade=True)

        if depasse_seuil_delegation(estimation.montant_estime):  # règle 5
            return self.conclure("Seuil de délégation dépassé", file="gestionnaire", avis=retenu,
                                 mode_degrade=degrade)
        motif = "Demande acceptée" + (" sans avis anti-fraude (mode dégradé, contrôle a posteriori)"
                                      if degrade else "")
        return self.conclure(motif, decision="acceptee", montant=estimation.montant_estime,  # règle 6
                             avis=retenu, mode_degrade=degrade)


def escalade_directe(reference: str, motif: str) -> dict[str, Any]:
    """Escalade motivée avant tout contrôle (pièces illisibles pour une raison technique, contrat incohérent) :
    la demande reçoit quand même une fiche, avec une étape de la Coordination."""
    return _Parcours({"reference": reference}, BORNES, partenaire_bouchon).conclure(motif, file="gestionnaire")


def traiter(demande: dict[str, Any], *, consulter: Callable[..., AvisFraude] = partenaire_bouchon,
            registre: RegistreAppels | None = None, bornes: Bornes = BORNES,
            limite: float | None = None) -> dict[str, Any]:
    """Traite une demande jusqu'à sa fiche de décision, quoi qu'il arrive.

    `limite` (horloge monotonic) : fin du budget de 10 s déjà commencé, par exemple pendant la lecture des pièces.
    """
    parcours = _Parcours(demande, bornes, appel_unique(consulter, registre or RegistreAppels()), limite)
    try:
        return parcours.derouler()
    except _BorneAtteinte as atteinte:
        return parcours.conclure(f"Arrêt par la borne « {atteinte.borne} » : reprise manuelle",
                                 file="gestionnaire", arret={"borne": atteinte.borne})
    except Exception as erreur:  # filet de sécurité : jamais de demande sans issue
        return parcours.conclure(f"Erreur interne ({type(erreur).__name__}) : reprise manuelle",
                                 file="gestionnaire")
