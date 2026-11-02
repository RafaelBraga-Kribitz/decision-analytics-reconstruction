# Decision-Analytics-Rekonstruktion — Präsidentschaftswahl Paraguay 2018

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Überblick

Dieses Projekt rekonstruiert die paraguayische Präsidentschaftswahl 2018 aus Sicht der Entscheidungsanalyse. Es verbindet drei Bausteine: synthetische Wählersegmente und Wahlbeteiligungsneigung, eine beschränkte Optimierung des Kampagnenbudgets sowie bayesianisches Umfrage-Monitoring mit Monte-Carlo-Szenarien.

Das verifizierte Wahlergebnis betrug **+3,70 Prozentpunkte** für Mario Abdo Benítez (46,43 % gegenüber 42,73 %); die Wahlbeteiligung lag bei 61,25 %. Als öffentliche Anker dienen Wahlergebnisse, Zensusdaten und acht veröffentlichte Umfragen. Einzelne Wählerdatensätze sind **synthetisch**; Tracking-Ergebnisse und Szenarien sind **illustrativ**.

Eine illustrative Wiederholung für Woche 8 verschiebt bei einem Budget von 6,03 Mio. US-Dollar 766.000 US-Dollar aus sechs umkämpften Departamentos. Das Modell schätzt dadurch 1,20 % mehr nach Überzeugungskraft gewichtete Kontakte. Das ist keine kausale Wirkungsschätzung: Die Gewichte wurden manuell angepasst, und am pessimistischen Rand des Intervalls kehrt sich der Effekt um.

## Was das Projekt zeigt

- Wählersegmentierung und Schätzung der Wahlbeteiligungsneigung.
- Budgetoptimierung mit gemischt-ganzzahliger linearer Programmierung (MILP) und Einsatzplanung.
- Bayesianisches Umfrage-Tracking und Szenarioanalyse.
- Klare Kennzeichnung verifizierter, kalibrierter, simulierter und illustrativer Ergebnisse.

## Wesentliche Grenzen

Das Projekt behauptet weder, dass die Analyse das Wahlergebnis verursacht hat, noch, dass das Modell Wahlen zuverlässig vorhersagt. Es gibt nur acht Umfragen und eine begrenzte Out-of-sample-Prüfung. Die Mikrodaten sind synthetisch. Das Optimierungsziel verwendet gewichtete Kontakte als Näherungswert statt empirisch geschätzter Medienwirkungskurven.

## Weiterlesen und ausführen

Das [vollständige README auf Englisch](README.md) enthält Ergebnisse, Architektur, Daten, Grenzen, Demos und Reproduktionsbefehle. Verwendet werden Python 3.11, Poetry und der feste Seed 42. Installieren Sie mit `poetry install`, prüfen Sie mit `make test` und starten Sie die Pipeline mit `make pipeline-full`.

[Repository und Demos](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction) · [Fallstudie](reports/CASE_STUDY.md) · [Epistemische Grenzen](reports/epistemic_boundaries.md)
