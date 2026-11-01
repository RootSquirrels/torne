"""The conformity gate — the truth table, and what it forbids.

These tests exercise the **socle**, not an adapter: the rule holds for every
source, whatever it is. It is written exactly once, in `verdict_from_criteria`,
and that is precisely what prevents an adapter from opening the gate on a
conformity that was never established.

The rule, in one sentence: **only `CONFORME` authorises use**. The three
other verdicts are an abstention or a finding of non-conformity, and
observations are never built on an abstention.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from torne.acquisition.contracts import (
    AcquisitionOutcome,
    AcquisitionRequest,
    AcquisitionStatus,
    Conformite,
    CritereConformite,
    Exhaustiveness,
    VerdictConformite,
    verdict_from_criteria,
    worst_verdict,
)

DEBUT = datetime(2026, 10, 31, 22, 0, tzinfo=UTC)


def _demande() -> AcquisitionRequest:
    return AcquisitionRequest(
        source_id="src-test",
        url="https://exemple.test/observations",
        label="test:observations",
    )


def _issue(verdict: VerdictConformite | None) -> AcquisitionOutcome:
    return AcquisitionOutcome(
        request=_demande(),
        status=AcquisitionStatus.SUCCESS,
        started_at=DEBUT,
        finished_at=DEBUT,
        exhaustiveness=Exhaustiveness.UNDECLARED,
        verdict_conformite=verdict,
    )


# --------------------------------------------------------------------------
# The truth table
# --------------------------------------------------------------------------


def test_no_criterion_gives_inapplicability():
    """The source declares no predicate: there is nothing to verify."""
    verdict = verdict_from_criteria({})

    assert verdict.conformite is Conformite.NON_APPLICABLE
    assert verdict.conforme is False
    assert verdict.motif is not None


def test_a_satisfied_criterion_gives_conformity():
    """Every requested criterion was verified, and every one is satisfied."""
    verdict = verdict_from_criteria(
        {"station": CritereConformite(demande="O919", verifie=True, recu="O919", conforme=True)}
    )

    assert verdict.conformite is Conformite.CONFORME
    assert verdict.conforme is True


def test_a_violated_criterion_gives_non_conformity():
    """A requested criterion was violated: that is a finding."""
    verdict = verdict_from_criteria(
        {"station": CritereConformite(demande="O919", verifie=True, recu="O919", conforme=False)}
    )

    assert verdict.conformite is Conformite.NON_CONFORME
    assert verdict.conforme is False
    assert "O919" in (verdict.motif or "")


def test_an_unverifiable_criterion_gives_indeterminacy():
    """Nothing violated, but at least one criterion remains unknown: abstention.

    This is the case the doctrine required from the start and that the socle
    did not apply: the unknown was never named. It now carries a verdict of
    its own, distinct from the finding of a violation.
    """
    verdict = verdict_from_criteria(
        {"cours_eau": CritereConformite(demande="O919", verifie=False, recu="field absent")}
    )

    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.conforme is False
    assert "conformity cannot be established" in (verdict.motif or "")


def test_a_finding_beats_an_abstention():
    """When one criterion is violated *and* another remains unknown, it is a finding.

    The order of the branches is not arbitrary: an established fact always
    takes precedence over silence.
    """
    verdict = verdict_from_criteria(
        {
            "station": CritereConformite(demande="O919", verifie=True, recu="X", conforme=False),
            "cours_eau": CritereConformite(demande="O919", verifie=False, recu="field absent"),
        }
    )

    assert verdict.conformite is Conformite.NON_CONFORME


def test_an_abstention_carries_its_motif():
    """It must be possible to say *what* could not be verified."""
    with pytest.raises(ValueError, match="motif"):
        VerdictConformite(conformite=Conformite.INDETERMINATE)


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conformite", "exploitable"),
    [
        (Conformite.CONFORME, True),
        (Conformite.INDETERMINATE, False),
        (Conformite.NON_APPLICABLE, False),
        (Conformite.NON_CONFORME, False),
    ],
)
def test_only_a_conformant_verdict_opens_the_gate(conformite, exploitable):
    """A single verdict authorises use: `CONFORME`.

    This is the rule that `test_une_absence_de_verdict_n_est_pas_une_conformite`
    already states for the absence of a check: nothing is certified that was
    not verified. It holds for the four verdicts.
    """
    issue = _issue(VerdictConformite(conformite=conformite, motif="motif"))

    assert issue.conformite is conformite
    assert issue.exploitable is exploitable


def test_an_issue_without_verdict_is_not_exploitable():
    """No verdict rendered: conformity is not established, and that is an abstention.

    A transport failure renders no verdict. It is not a conformity, and it is
    not an inapplicability either: it is silence, and silence opens
    nothing.
    """
    issue = _issue(None)

    assert issue.conformite is Conformite.INDETERMINATE
    assert issue.exploitable is False


# --------------------------------------------------------------------------
# Worst wins
# --------------------------------------------------------------------------


def test_the_most_unfavourable_verdict_wins():
    """A page that could not be certified cannot be covered by a conformant page.

    The traversal spans several pages, and each of them is checked. The
    issue carries the most severe verdict: it is the only reading that stops
    a late conformant page from covering a page that could not be certified.
    """
    verdicts = [
        VerdictConformite(conformite=Conformite.CONFORME),
        VerdictConformite(conformite=Conformite.INDETERMINATE, motif="motif"),
        VerdictConformite(conformite=Conformite.CONFORME),
    ]

    pire = worst_verdict(verdicts)

    assert pire is not None
    assert pire.conformite is Conformite.INDETERMINATE


def test_no_verdict_gives_no_verdict():
    """A traversal without any check gives nothing to decide."""
    assert worst_verdict([]) is None


def test_an_issue_inherits_the_most_unfavourable_verdict():
    """The gate sees the most severe verdict, not the last one rendered."""
    issue = _issue(VerdictConformite(conformite=Conformite.INDETERMINATE, motif="motif"))

    assert issue.exploitable is False
