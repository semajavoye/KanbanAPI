# KanbanAPI

Enterprise-grade Integrations-API zur Anbindung von **Microsoft Navision**, **PowerDB** und **PostgreSQL**.
Bereitgestellt für die interne **KanbanSoftware**, entwickelt auf Basis von **Django**, **Django REST Framework (DRF)** und **drf-spectacular**.

Die API fungiert als zentraler Data-Gateway-Layer, der heterogene Datenquellen konsistent, sicher und skalierbar für nachgelagerte Systeme verfügbar macht.

---

## Architekturüberblick

Die KanbanAPI abstrahiert sämtliche Zugriffe auf Navision, PowerDB und zusätzliche Datenbanken.
Der Service implementiert:

* einheitliche Endpunkte für Kanban-Prozesse
* zuverlässige Orchestrierung von Lese- und Schreiboperationen
* internes Caching und Connection-Pooling
* konsistente Datenvalidierung und Fehlerbehandlung
* vollständige API-Dokumentation via drf-spectacular

Der Fokus liegt auf klar definierten Geschäftsoperationen statt einzelner Tabellenabfragen.
Die API ist vollständig **stateless** und horizontal skalierbar.

---

## Technologie-Stack

| Komponente                | Beschreibung                                   |
| ------------------------- | ---------------------------------------------- |
| **Python 3.x**            | Basislaufzeit                                  |
| **Django**                | Applikations-Framework                         |
| **Django REST Framework** | API-Engine                                     |
| **drf-spectacular**       | API-Documentation-Generation                   |
| **psycopg2**              | DB-Konnektivität (Navision, PowerDB)           |
| **Redis (optional)**      | Caching und Rate-Limiting                      |
| **Gunicorn**              | WSGI Server                                    |
| **Nginx / Ingress**       | Bereitstellung auf K8s                         |

---

## API-Dokumentation

Die vollständige API-Dokumentation wird automatisch generiert über **drf-spectacular** und steht bereit unter:

* **/api/schema/** – API Schema
* **/api/docs/** – Interaktive Swagger UI

Alle Endpunkte folgen konsistenten Richtlinien bzgl. Naming, Fehlercodes und Response-Strukturen.

---

## Zielsetzung

Die KanbanAPI ist der zentrale Backbone der KanbanSoftware-Architektur. Sie ermöglicht:

* robuste Kommunikation zwischen Maschinen, Software und Datenbanken
* klare Schnittstellen und geringere Kontextkopplung
* klare Wartungs- und Erweiterbarkeit
* vereinfachung, sodass die Software nicht direkt mit dem Code auf die Datenbank zugreifen muss

Diese API bildet die Grundlage für alle zukünftigen Erweiterungen im Bereich Wareneingang, Kanban-Prozesse, RFID-Anbindung und systemweite Datenkonsistenz.
