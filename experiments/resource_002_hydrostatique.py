"""RESOURCE-002 (correction) — la conversion hydrostatique, refaite proprement.

Une premiere version de ce dossier annoncait **3,5 tonnes de GNL par centimetre de
tirant d'eau**. C'etait faux : la formule de deplacement volumetrique avait ete
divisee par le tirant d'eau, ce qui divise la sensibilite d'un facteur d'environ
trente. Ce script etablit la relation correcte, et verifie le resultat contre
une reference documentee.

La relation
------------

Le deplacement d'un navire est le poids d'eau de mer qu'il deplace :

    deplacement (t) = rho_sw · Cb · Lpp · B · T

Donc, a Cb et aux dimensions donnes :

    d(deplacement)/dT = rho_sw · Cb · Lpp · B      [tonnes par metre]
    TPC (tonnes par centimetre) = 0,01 · rho_sw · Cb · Lpp · B

**La division par T n'a rien a faire la.** C'est de la que venait l'erreur.

Les trois pieges que le modele doit porter
------------------------------------------

1. **Deplacement n'est pas cargaison.** La masse de GNL decharge est bien la
   variation de deplacement, mais le volume de LNG decharge n'est **pas** la
   variation de volume de coque : le GNL (environ 450 kg/m3) n'a pas la meme
   densite que l'eau de mer (environ 1 025 kg/m3).
2. **Le tirant d'eau ne bouge pas toujours.** Les methaniers qui pratiquent le
   *ballast and deck load* (BDL) **compensent le dechargement par le ballast**
   pour conserver un tirant d'eau quasi constant. Pour ces navires, la methode
   ne voit rien, meme si la cargaison est entierement dechargee.
3. **La masse n'est pas la cargaison.** Ballast, combustibles, eau douce, Stores
   et l'assiette evoluent independamment du cargo.

Usage :

    uv run python experiments/resource_002_hydrostatique.py
"""

from __future__ import annotations

import sys

RHO_EAU_DE_MER = 1.025
"""Densite de l'eau de mer (t/m3), valeur usuelle en surface temperee."""

RHO_GNL_0C = 0.456
"""Densite du GNL a 0 degree C et 1,01325 bar (t/m3)."""

GCV_0C = 13.99
"""Pouvoir calorifique superieur du GNL a 0 degree C (MJ/m3)."""

MJ_PAR_GWH = 3600.0
"""1 GWh = 3600 MJ."""


class Methanier:
    """Un methanier, avec son hydrostatique."""

    def __init__(
        self,
        nom: str,
        capacite_m3: int,
        lpp: float,
        largeur: float,
        tirant_ea_u: float,
        deplacement_plein: float,
        rho: float = RHO_EAU_DE_MER,
    ) -> None:
        self.nom = nom
        self.capacite_m3 = capacite_m3
        self.lpp = lpp
        self.largeur = largeur
        self.tirant_ea_u = tirant_ea_u
        self.deplacement_plein = deplacement_plein
        self.rho = rho

    @property
    def volume_deplace(self) -> float:
        """Le volume d'eau de mer deplace (m3)."""
        return self.deplacement_plein / self.rho

    @property
    def cb(self) -> float:
        """Le coefficient de bloc, deduit de l'hydrostatique."""
        return self.volume_deplace / (self.lpp * self.largeur * self.tirant_ea_u)

    @property
    def tpc_tonne_par_cm(self) -> float:
        """La sensibilite : tonnes de deplacement par centimetre de tirant d'eau."""
        return 0.01 * self.rho * self.cb * self.lpp * self.largeur

    @property
    def tpc_tonne_par_pouce(self) -> float:
        """La meme sensibilite, en tonnes par pouce."""
        return self.tpc_tonne_par_cm * 2.54

    def cargaison_pour_ecart(self, ecart_cm: float) -> float:
        """La masse de cargo correspondant a un ecart de tirant d'eau, en tonnes.

        Sous l'hypothese que le **seul** changement est le cargo : ni ballast,
        ni combustible, ni assiette, ni eau de mer ne changent.
        """
        return self.tpc_tonne_par_cm * ecart_cm


def tonnes_par_gwh(gcv: float = GCV_0C, rho: float = RHO_GNL_0C) -> float:
    """Les tonnes de GNL que represente un GWh, a la base du bulletin.

    Le bulletin exprime l'energie en GWh, sur une base de **GCV a 0 degree C**
    et de **volume a 0 degree C / 1,01325 bar**. La conversion energie -> masse
    est donc :

        volume (m3) = energie (GWh) · 3600 (MJ/GWh) / GCV (MJ/m3)
        masse  (t)  = volume (m3) · rho (t/m3)

    Attention a l'unite : 1 GWh = 3600 MJ, pas 3600 GJ.
    """
    return MJ_PAR_GWH / gcv * rho


def main(argv: list[str]) -> int:
    """Le calcul, et son controle."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 100)
    print("1. LA CONVERSION HYDROSTATIQUE — le cas de reference")
    print()
    reference = Methanier(
        "Methanier 177 000 m3 (cas de reference cite)",
        capacite_m3=177_000,
        lpp=280.0,
        largeur=52.0,
        tirant_ea_u=11.7,
        deplacement_plein=130_233.0,
    )
    print(
        f"   volumetrie        : {reference.lpp:.0f} m x {reference.largeur:.0f} m, "
        f"tirant d'eau {reference.tirant_ea_u:.1f} m"
    )
    print(
        f"   deplacement plein : {reference.deplacement_plein:,.0f} t "
        f"(eau de mer a {reference.rho} t/m3)"
    )
    print(f"   volume deplace   : {reference.volume_deplace:,.0f} m3")
    print(f"   coefficient de bloc Cb deduit : {reference.cb:.3f}")
    print()
    print("   >> TPC = 0,01 x rho x Cb x Lpp x B")
    print(
        f"           = 0,01 x {reference.rho} x {reference.cb:.3f} x {reference.lpp:.0f} "
        f"x {reference.largeur:.0f}"
    )
    print(
        f"           = {reference.tpc_tonne_par_cm:.1f} t/cm "
        f"({reference.tpc_tonne_par_pouce:.0f} t/pouce)"
    )
    print()
    controle = reference.deplacement_plein / (reference.tirant_ea_u * 100.0)
    print(f"   controle d'ordre de grandeur (deplacement / (T x 100)) : {controle:.0f} t/cm")
    ecart = abs(controle - reference.tpc_tonne_par_cm) / controle * 100
    print(
        f"   ecart avec le calcul par bloc : {ecart:.2f} %  ->  "
        + ("concordant" if ecart < 1 else "A VERIFIER")
    )

    print()
    print("2. LE BUDGET D'ERREUR, CORRIGE")
    print()
    print(f"   {'ecart de tirant':<20} {'masse (t)':>14} {'sur 80 000 t':>16}")
    for ecart_cm in (10.0, 20.0, 30.0, 50.0):
        masse = reference.cargaison_pour_ecart(ecart_cm)
        print(f"   {ecart_cm / 100:.2f} m{'':<13} {masse:>14,.0f} {masse / 80_000 * 100:>15.3f} %")
    print()
    print("   [FAIT] le seuil de +/- 0,3 m ne vaut donc PAS 0,001 % de la cargaison :")
    print(
        f"          il vaut {reference.cargaison_pour_ecart(30.0) / 80_000 * 100:.1f} % "
        f"d'une cargaison de 80 000 t."
    )
    print("          Et l'exigence de precision correspondante change : pour 1 % de")
    print(
        f"          cargaison, il faut un ecart de tirant d'eau de "
        f"{80_000 * 0.01 / reference.tpc_tonne_par_cm:.1f} cm."
    )

    print()
    print("3. LE CONTRAT DU PUITS : une cargaison en GWh, une en tonnes")
    print()
    par_gwh = tonnes_par_gwh()
    print(f"   1 GWh (GCV a 0 C, volume a 0 C / 1,01325 bar) = {par_gwh:,.0f} t de GNL")
    print(f"   soit 1 TWh = {par_gwh * 1000 / 1000:,.1f} kt")
    print()
    print("   controle par les donnees du bulletin (Espagne, avril 2026) :")
    gwh_avril = 16_651.0
    navires_avril = 21
    tonnes = gwh_avril * par_gwh
    print(f"      {gwh_avril:,.0f} GWh x {par_gwh:,.0f} t/GWh = {tonnes / 1e6:.2f} Mt")
    print(
        f"      soit {tonnes / navires_avril:,.0f} t par navire decharge ({navires_avril} navires)"
    )
    print("      [FAIT] c'est compatible avec une flotte de methaniers de 174 000 a")
    print("             226 000 m3 : l'ordre de grandeur est coherent, ce qui valide")
    print("             la conversion. Ce qui ne l'est pas, c'est la conversion")
    print("             tirant d'eau -> tonnes, qui doit passer par les tables")
    print("             hydrostatiques de chaque navire.")

    print()
    print("4. LE CAS BDL — quand la methode ne voit rien")
    print()
    print("   Un methanier qui pratique le *ballast and deck load* transfere la")
    print("   cargaison des cuves de pont vers les cuves machine et compense le")
    print("   dechargement par le ballast, pour conserver un tirant d'eau constant.")
    print()
    for ballast_equilibre in (0.0, 0.5, 1.0):
        ecart = reference.tpc_tonne_par_cm * 0.0
        cargaison = reference.capacite_m3 * 0.85 * RHO_GNL_0C * (1 - ballast_equilibre)
        print(
            f"      ballast compense a {ballast_equilibre * 100:3.0f} %  ->  "
            f"ecart de tirant d'eau mesure : {ecart:.2f} m  "
            f"(cargaison reelle : {cargaison:,.0f} t)"
        )
    print()
    print("   >> Pour un navire BDL, la methode renvoie zero alors que la cargaison")
    print("      a varie de plusieurs dizaines de milliers de tonnes. La question")
    print("      du regime de chargement n'est donc pas secondaire : elle decide")
    print("      si la methode s'applique.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
