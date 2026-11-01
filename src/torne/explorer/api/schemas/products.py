"""The published knowledge products, as the API serves them.

A product that is published on disk is served as it is: its identity, its
lineage, the bounds it declares, and the states it carries.

Two rules shape these schemas:

- **A field that is not known is `null`.** It is never replaced by a zero, by
  an empty string, or by a plausible default. The published payload keeps its
  absences, and so does the API: the first day of a series has no derived
  entry because it has no previous day, and the API says so with a null.
- **The application does not modify the product it consumes.** The numbers
  served are the numbers the published record carries. Nothing here is
  recomputed, rounded or reinterpreted.

The indicators are typed, and they are typed for **one** product: the European
gas supply. The generic half of the chain — the store, the record, the list of
products — knows nothing about gas. This is the first application of the
first product, and it says so rather than pretending to be a registry.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "AggregateSumControl",
    "ConfrontationRow",
    "ConfrontationRows",
    "CountryDependency",
    "LossScenario",
    "ProductBound",
    "ProductDetail",
    "ProductLayer",
    "ProductList",
    "ProductQuantity",
    "ProductRef",
    "ProductState",
    "ProductStates",
    "ProductSummary",
    "ProductUnits",
    "ProductValidation",
    "ProductWindow",
    "SourceDescription",
    "StorageConcentration",
    "StorageCountryIndicator",
    "StorageIndicators",
    "StorageProvenance",
    "StorageUnits",
    "TerminalConcentration",
    "TerminalIndicators",
    "TerminalState",
]


class ProductRef(BaseModel):
    """One link of a product's lineage."""

    kind: str = Field(
        description="What the reference points at: a source, an observation, an evaluation."
    )
    identifier: str = Field(description="The stable identifier of the object cited.")
    label: str | None = Field(default=None, description="A human-readable name for it.")
    revision: str | None = Field(default=None, description="Its version, when it has one.")


class ProductSummary(BaseModel):
    """A published product, as the list shows it."""

    product_id: str = Field(description="The stable identifier of the product.")
    version: str = Field(description="The version of the product. A correction is a new version.")
    title: str = Field(description="What the product is.")
    status: str = Field(description="Its status: usable, degraded, withdrawn or inconclusive.")
    nature: str = Field(description="The nature of the result it publishes.")
    produced_at: str = Field(description="When the product was established.")
    domain_of_validity: str = Field(description="Where the product holds, and where it does not.")
    uncertainty: str = Field(description="Its uncertainty, qualified in clear language.")
    payload_digest: str = Field(description="The digest of the payload it publishes.")


class ProductList(BaseModel):
    """The products the repository has published."""

    products: list[ProductSummary] = Field(description="The published products.")


class ProductQuantity(BaseModel):
    """A quantity the product publishes, with what it means and in what unit."""

    label: str = Field(description="What the quantity is.")
    unit: str | None = Field(default=None, description="The unit it is expressed in.")


class ProductLayer(BaseModel):
    """One physical layer of a product, and the columns it publishes."""

    id: str = Field(description="The layer's identifier.")
    title: str = Field(description="What the layer is.")
    file: str = Field(description="The published file that carries it.")
    entity_column: str = Field(description="The column that names the entity the state belongs to.")
    label_column: str = Field(description="The column that names it for a reader.")
    country_column: str = Field(description="The column that carries its country.")
    day_column: str = Field(description="The column that carries the gas day.")
    published_column: str = Field(description="The column that carries the publication instant.")
    position_columns: list[str] = Field(
        default_factory=list, description="The columns that place it."
    )
    measures: dict[str, ProductQuantity] = Field(
        default_factory=dict, description="The quantities it publishes, by column."
    )
    flags: dict[str, ProductQuantity] = Field(
        default_factory=dict, description="The flags it publishes, by column."
    )


class ProductWindow(BaseModel):
    """The period a layer covers.

    The counts are optional: a layer that publishes its own window may count
    its states and entities, and a window that only bounds the period says
    so. A count that is not published stays null.
    """

    start: str = Field(description="The first day of the period.")
    end: str = Field(description="The last day of the period.")
    states: int | None = Field(default=None, description="How many states the period holds.")
    entities: int | None = Field(default=None, description="How many entities the period covers.")


class ProductUnits(BaseModel):
    """The units the product's quantities are expressed in.

    The measures are the units of the columns of the payload; the published
    ones are the units each source states for itself.
    """

    measures: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="The unit of each measure, by layer and by column."
    )
    published: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="The units each source publishes for itself, by layer."
    )


class ProductBound(BaseModel):
    """A quantity that is a bound, and not a measurement."""

    quantity: str = Field(description="What the bound concerns.")
    direction: str = Field(description="`lower` or `upper`: which way the true value lies.")
    statement: str = Field(description="Why the quantity is a bound, in clear language.")


class ProductValidation(BaseModel):
    """The confrontation that validated the product, and what it found."""

    method: str = Field(description="How the product was confronted with an independent source.")
    comparisons: int = Field(description="How many comparisons were made.")
    median_relative_difference: float | None = Field(
        default=None, description="The median relative difference, as a fraction."
    )
    max_relative_difference: float | None = Field(
        default=None, description="The largest relative difference, as a fraction."
    )
    median_relative_difference_volume: float | None = Field(
        default=None, description="The median relative difference on the volumes."
    )
    median_relative_difference_network_flow: float | None = Field(
        default=None, description="The median relative difference on the network flow."
    )
    aligned_days: str | None = Field(
        default=None, description="How the two sources' days were aligned."
    )
    residual: str | None = Field(
        default=None, description="What the residual difference turned out to be."
    )


class ProductProvenance(BaseModel):
    """Where the product's numbers come from."""

    sources: list[SourceDescription] = Field(
        default_factory=list, description="The sources it consumed."
    )
    identifier_reference: str | None = Field(
        default=None, description="Where the identifiers of the entities come from."
    )
    production_digests: dict[str, str] = Field(
        default_factory=dict,
        description="The digest of each production file the product was built from.",
    )


class SourceDescription(BaseModel):
    """One source the product consumed."""

    source_id: str = Field(description="The source's identifier.")
    publisher: str = Field(description="Who publishes it.")
    dataset: str = Field(description="Which dataset of theirs it is.")
    units: str = Field(description="The units it publishes.")
    access: str = Field(description="How it is reached.")
    identifier_reference: str | None = Field(
        default=None,
        description="Where the identifiers of the entities come from, when it is not this source.",
    )


class TerminalConcentration(BaseModel):
    """How the reserve is concentrated among the installations."""

    herfindahl: float = Field(
        description="The Herfindahl index of the reserve among the installations."
    )
    top_share: float = Field(description="The share of the reserve the first installation carries.")
    top_three_share: float = Field(description="The share the three first carry.")
    total_gwh: float = Field(description="The European reserve, in GWh.")


class CountryDependency(BaseModel):
    """What one country holds, and what it lets out."""

    stock_gwh: float = Field(description="Its reserve, in GWh.")
    capacity_gwh: float = Field(description="Its capacity, in GWh.")
    send_out_gwh_per_day: float = Field(description="Its send-out, in GWh per day.")
    terminals: float = Field(description="How many terminals it holds.")
    stock_share: float = Field(description="Its share of the European reserve.")
    capacity_share: float = Field(description="Its share of the European capacity.")
    send_out_share: float = Field(description="Its share of the European send-out.")


class AggregateSumControl(BaseModel):
    """The control of a country's terminals against the aggregate it publishes."""

    country: str = Field(description="The country.")
    terminals_counted: int = Field(description="How many terminals were counted.")
    terminals_sum_gwh: float = Field(description="The sum of the terminals' reserves, in GWh.")
    published_aggregate_gwh: float = Field(
        description="The aggregate the platform publishes, in GWh."
    )
    relative_difference: float = Field(description="The difference between the two, as a fraction.")


class LossScenario(BaseModel):
    """What the loss of one installation costs the system."""

    installation: str = Field(description="The installation that is lost.")
    coverage_before_days: float = Field(description="The coverage before, in days.")
    coverage_after_days: float = Field(description="The coverage after, in days.")
    days_lost: float = Field(description="The days of coverage it costs.")
    reserve_lost_gwh: float = Field(description="The reserve it carries, in GWh.")
    flow_lost_gwh_per_day: float = Field(description="The send-out it carries, in GWh per day.")
    reserve_share_lost: float = Field(description="Its share of the European reserve.")


class TerminalIndicators(BaseModel):
    """What the terminal layer publishes."""

    product: str = Field(description="The product, in the words of the mission that produced it.")
    generated_at: str = Field(description="When the indicators were computed.")
    window: ProductWindow = Field(description="The period they cover.")
    reference_date: str = Field(description="The day they are the state of.")
    sources: list[SourceDescription] = Field(
        default_factory=list, description="The sources they come from."
    )
    concentration: TerminalConcentration = Field(description="How the reserve is concentrated.")
    concentration_by_country: float = Field(
        description="The Herfindahl index of the reserve among the countries."
    )
    dependency_by_country: dict[str, CountryDependency] = Field(
        default_factory=dict, description="What each country holds and lets out."
    )
    aggregate_sum_control: list[AggregateSumControl] = Field(
        default_factory=list,
        description="The control of each country's terminals against its aggregate.",
    )
    installations_without_data: list[str] = Field(
        default_factory=list,
        description="The installations the platform lists but publishes nothing for.",
    )
    system_coverage_days: float = Field(
        description="The coverage of the system, in days. It is an upper bound."
    )
    system_reserve_gwh: float = Field(description="The exploitable reserve of the system, in GWh.")
    system_flow_gwh_per_day: float = Field(
        description="The send-out of the system, in GWh per day."
    )
    loss_scenarios: list[LossScenario] = Field(
        default_factory=list, description="What the loss of each installation costs."
    )
    installations: int = Field(description="How many installations the layer carries.")
    states: int = Field(description="How many states the layer holds.")


class StorageConcentration(BaseModel):
    """How the reserve is concentrated among the countries."""

    herfindahl: float = Field(description="The Herfindahl index of the national reserves.")
    top_country_share: float = Field(description="The share the first country carries.")
    top_three_countries_share: float = Field(description="The share the three first carry.")


class StorageCountryIndicator(BaseModel):
    """What one country's underground storage holds."""

    country: str = Field(description="The country.")
    days: int = Field(description="How many days of the period it covers.")
    stock_gwh: float = Field(description="Its reserve, in GWh.")
    capacity_gwh: float = Field(description="Its capacity, in GWh.")
    published_fill_pct: float = Field(description="The published fill, in per cent.")
    computed_coverage_days: float = Field(
        description="The computed coverage, in days. It is an upper bound."
    )
    published_autonomy_days: float = Field(
        description="The autonomy the platform publishes, in days."
    )
    published_autonomy_on_consumption_days: float = Field(
        description="The published autonomy divided by the published consumption, in days."
    )
    published_autonomy_over_consumption_ratio: float = Field(
        description="The ratio of the published autonomy to the published consumption."
    )
    difference_with_published_days: float = Field(
        description="The difference between the computed coverage and the published autonomy, in days."
    )
    reconstitution_rate_per_day: float = Field(description="How fast it refills, per day.")
    degradation_days_per_day: float = Field(
        description="How fast it draws down, in days of coverage per day."
    )
    published_at: str = Field(description="When the state was published.")


class StorageUnits(BaseModel):
    """The units the storage layer publishes."""

    stock: str = Field(description="The unit of the reserves.")
    flow: str = Field(description="The unit of the flows.")


class StorageProvenance(BaseModel):
    """Where the storage layer's numbers come from."""

    source: str = Field(description="The platform that publishes them.")
    attribution: str = Field(description="The attribution it requires.")
    api: str = Field(description="How it is reached.")
    credential: str = Field(description="How the key is carried.")


class StorageIndicators(BaseModel):
    """What the storage layer publishes."""

    period: ProductWindow = Field(description="The period it covers.")
    coverage: list[str] = Field(
        default_factory=list, description="The countries the platform answered for."
    )
    countries_without_published_state: list[str] = Field(
        default_factory=list,
        description="The countries it answered for that published no usable state. "
        "They are not missing data: they are declared absences.",
    )
    refusals: list[str] = Field(default_factory=list, description="The refusals it recorded.")
    indicators: list[StorageCountryIndicator] = Field(
        default_factory=list, description="What each country holds."
    )
    concentration: StorageConcentration = Field(description="How the reserve is concentrated.")
    units: StorageUnits = Field(description="The units it publishes.")
    provenance: StorageProvenance = Field(description="Where its numbers come from.")


class ProductIndicators(BaseModel):
    """The indicators of each layer of the product.

    They are typed, layer by layer, because a reader must be able to trust
    what a number means without reading the production code that produced it.
    """

    terminals: TerminalIndicators = Field(description="What the LNG terminal layer publishes.")
    storage: StorageIndicators = Field(description="What the underground storage layer publishes.")


class ProductDetail(BaseModel):
    """A published product, in full."""

    product_id: str = Field(description="The stable identifier of the product.")
    version: str = Field(description="The version of the product.")
    title: str = Field(description="What the product is.")
    nature: str = Field(description="The nature of the result it publishes.")
    produced_at: str = Field(description="When the product was established.")
    generated_at: str | None = Field(
        default=None, description="When the published payload was generated."
    )
    reference_date: str | None = Field(
        default=None, description="The day the published states are the state of."
    )
    status: str = Field(description="Its status: usable, degraded, withdrawn or inconclusive.")
    domain_of_validity: str = Field(description="Where the product holds, and where it does not.")
    uncertainty: str = Field(description="Its uncertainty, qualified in clear language.")
    lineage: list[ProductRef] = Field(
        description="Its lineage, from the sources to the evaluation."
    )
    input_statuses: dict[str, str] = Field(
        description="The quality status of each entry it consumed."
    )
    provisional_inputs: list[str] = Field(
        default_factory=list, description="The entries it consumed whose status is provisional."
    )
    payload_digest: str = Field(description="The digest of the payload it publishes.")
    payload_files: list[str] = Field(description="The files the payload is made of.")
    windows: dict[str, ProductWindow] = Field(description="The period each layer covers.")
    layers: dict[str, ProductLayer] = Field(
        description="The layers it publishes, and the columns they carry."
    )
    bounds: list[ProductBound] = Field(
        description="The quantities that are bounds, not measurements."
    )
    units: ProductUnits = Field(description="The units its quantities are expressed in.")
    validation: ProductValidation = Field(description="The confrontation that validated it.")
    provenance: ProductProvenance = Field(description="Where its numbers come from.")
    indicators: ProductIndicators = Field(
        description="The indicators of each layer, typed by the layer they belong to."
    )


class ProductState(BaseModel):
    """One state of one entity."""

    entity: str = Field(description="The entity the state belongs to.")
    label: str = Field(description="Its name for a reader.")
    country: str = Field(description="Its country.")
    gas_day: str = Field(description="The day the state describes.")
    published_at: str = Field(description="When the state was published.")
    values: dict[str, float | None] = Field(
        description="The quantities of the state. A quantity that is not known is null."
    )
    flags: dict[str, bool | None] = Field(description="The flags of the state.")
    latitude: float | None = Field(default=None, description="Its latitude, when it is placed.")
    longitude: float | None = Field(default=None, description="Its longitude, when it is placed.")


class ProductStates(BaseModel):
    """The states of one layer."""

    product_id: str = Field(description="The product the states belong to.")
    layer: str = Field(description="The layer they belong to.")
    states: list[ProductState] = Field(description="The states themselves.")


class TerminalState(ProductState):
    """One state of one LNG terminal."""


class ConfrontationRow(BaseModel):
    """One day of one terminal, seen by two independent sources."""

    operator_terminal: str = Field(description="The terminal, in the operator's words.")
    terminal_eic: str = Field(description="Its identifier.")
    alsi_day: str = Field(description="The day the platform describes.")
    operator_day: str = Field(description="The day the operator describes.")
    alsi_stock_gwh: float | None = Field(
        default=None, description="The stock the platform publishes, in GWh."
    )
    operator_stock_gwh: float | None = Field(
        default=None, description="The stock the operator publishes, in GWh."
    )
    absolute_difference_gwh: float | None = Field(
        default=None, description="The difference between the two, in GWh."
    )
    relative_difference: float | None = Field(
        default=None, description="The difference between the two, as a fraction."
    )


class ConfrontationRows(BaseModel):
    """The confrontation, in full."""

    product_id: str = Field(description="The product the confrontation validates.")
    comparisons: int = Field(description="How many comparisons it holds.")
    rows: list[ConfrontationRow] = Field(description="The comparisons themselves.")
