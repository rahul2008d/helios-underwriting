"""Underwriting appetite rules for the Helios fictional insurer.

These rules define what risks the carrier wants to write. They're used as
the system prompt context for the triage agent. In a real insurer these
would be far more complex and stored in a rules engine.
"""

APPETITE_GUIDELINES = """
Helios Underwriting writes UK and European commercial fleet insurance.

# Target appetite (ACCEPT)
- Fleet size between 2 and 100 vehicles.
- Annual revenue between GBP 100,000 and GBP 50,000,000.
- Operations primarily in the UK; European operations acceptable for established carriers.
- Commercial vehicles: vans, lorries, articulated HGVs, refrigerated transport.
- Drivers with 5+ years experience and 6 or fewer penalty points.
- Loss ratio under 60% over the last 5 years (claims value vs estimated 5y premium).
- Stable trading history (3+ years recommended).

# Edge cases (REFER to senior underwriter)
- Hazardous goods carriers (require ADR specialist review).
- Specialist plant or recovery vehicles.
- Fleets with 50+ vehicles (require capacity check).
- Operations outside Europe.
- Claims frequency above 1.5 claims per vehicle per year.
- Fleets with multiple drivers under age 25.

# Outside appetite (DECLINE)
- Fleets primarily operating in conflict zones or sanctioned countries.
- Drivers with disqualifications, drink-driving, or drug-driving convictions.
- Loss ratio over 100% over the last 5 years.
- Companies in liquidation or with active CCJs.
- Vehicles over 25 years old (vintage requires specialist cover).
- Single-vehicle policies (we do not underwrite individual vehicles).
"""
