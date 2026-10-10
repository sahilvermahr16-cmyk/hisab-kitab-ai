from typing import List, Any
from pydantic import BaseModel, Field
from enum import Enum

from models import MovementEntityType

class Action(BaseModel):
    text: str
    date: str

class UserIntent(BaseModel):
    actions: List[Action]

class RecordType(str, Enum):
    NEED_PERSON = "Need Person"
    MATERIAL_MOVEMENT = "Material Movement"
    STANDALONE_TRANSACTION = "Standalone Transaction"
    CORRECTION = "Correction"

class ActionGroup(BaseModel):
    group_id: str
    record_type: RecordType = Field(
        description="The generic category used only for grouping extracted actions. "
        "Need Person is used when a specifically named individual is mentioned "
        "but their business role is ambiguous. "
        "Material Movement is used whenever material/item movement between a "
        "source and destination is explicitly described. "
        "Standalone Transaction is used for non-material business events that "
        "are not unresolved named-person cases. "
        "Correction is used when the user is explicitly reporting that a "
        "PREVIOUSLY recorded entry was wrong and needs to be fixed — never "
        "used for a brand-new business event. "
        "Do NOT classify IN, OUT, Direct Sale, or Internal Movement at this stage. "
        "Those are determined later using resolved business/location information."
    )
    identity_key: str = Field(
        description="The exact identity key used to group actions. "
        "For Need Person, use the person's name. "
        "For Material Movement, use the explicitly stated "
        "source→destination pair. "
        "Do not invent, assume, or infer a missing source or destination. "
        "If source or destination is not explicitly available, preserve "
        "the missing part as UNKNOWN rather than guessing. "
        "For Standalone Transaction, use the explicit transaction or "
        "entity identity present in the action. "
        "Two groups with the same record_type but different identity_key "
        "values are always different groups."
    )
    actions: List[Action]
    need_person: bool | None = None

class NeedPerson(BaseModel):
    need_person: bool | None = None

class GroupedIntent(BaseModel):
    groups: List[ActionGroup]

class PersonRole(str, Enum):
    EMPLOYEE = "Employee"
    CUSTOMER = "Customer"
    SUPPLIER = "Supplier"
    PROPERTY_OWNER = "Property / Site Owner"
    FAMILY_MEMBER = "Family Member"

class PersonRoleClassificationInput(BaseModel):
    """
    Input provided to the Person Role Classification & Ranking LLM.
    Each input represents exactly one Action Group.
    """
    group_id: str = Field(description="Unique Action Group identifier.")
    actions: List[Action] = Field(description="All business actions belonging to the same Action Group.")

class PersonRoleClassificationResult(BaseModel):
    """
    Structured output returned by the LLM for one Action Group.

    The LLM must assign an independent confidence score
    (0-10) for EVERY supported person role.

    Confidence scores are independent.

    They are NOT probabilities and DO NOT need to sum to 10.

    Use ONLY the supported roles below.
    Do NOT invent new roles.
    """
    group_id: str = Field(description="Unique Action Group identifier.")
    person: str = Field(description="The person whose business role is being classified "
            "for this Action Group."
        )
    employee: float = Field( ge=0, le=10, description="Independent Confidence (0-10) that the person is an Employee.")
    customer: float = Field( ge=0, le=10, description="Independent Confidence (0-10) that the person is a Customer.")
    supplier: float = Field(ge=0, le=10, description="Independent Confidence (0-10) that the person is a Supplier.")
    property_owner: float = Field(ge=0, le=10, description="Independent Confidence (0-10) that the person is a Property / Site Owner.")
    family_member: float = Field(ge=0, le=10, description="Independent Confidence (0-10) that the person is a Family Member.")

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class RankedRole(BaseModel):
    """
    One candidate role after ranking.
    """
    role: PersonRole = Field(description="Supported person role.")
    confidence: float = Field(ge=0, le=10, description="Confidence score assigned to this role.")

class PersonRoleRankingResult(BaseModel):
    """
    Output of the Person Role Classification & Ranking node.
    This schema is produced AFTER:
    - LLM role classification
    - Python ranking
    - Confidence evaluation
    - Recommendation generation
    """
    group_id: str = Field(description="Unique Action Group identifier.")
    person: str = Field(description="Person whose role has been classified.")
    confidence_level: ConfidenceLevel = Field(description=("Overall confidence level calculated by the node."))
    ranking: List[RankedRole] = Field(description=("All supported roles sorted from highest to lowest confidence."))

class HITLInteractionType(str, Enum):
    CONFIRMATION = "CONFIRMATION"
    SELECTION = "SELECTION"

class HITLReason(str, Enum):
    HIGH_CONFIDENCE_CONFIRMATION = "HIGH_CONFIDENCE_CONFIRMATION"
    MEDIUM_CONFIDENCE_SELECTION = "MEDIUM_CONFIDENCE_SELECTION"
    LOW_CONFIDENCE_SELECTION = "LOW_CONFIDENCE_SELECTION"
    # Naam pehle se hisab mein hai (employee / customer / ... table mein mila)
    KNOWN_PERSON_CONFIRMATION = "KNOWN_PERSON_CONFIRMATION"   # sirf ek category mein mila → confirm karo
    KNOWN_PERSON_SELECTION = "KNOWN_PERSON_SELECTION"         # kai category mein mila → ✓ ke saath chuno

class HITLOption(BaseModel):
    option_id: int = Field(description="Unique option identifier.")
    role: PersonRole = Field(description="Candidate role.")
    confidence: float = Field(ge=0, le=10, description="Confidence score assigned to this role.")
    found: bool = Field(default=False, description="True if this person's name already exists in this role's records.")

class PersonRoleHITLRequest(BaseModel):
    """
    Structured request sent to the UI layer.
    The backend never generates user-facing text.
    The UI (Terminal / React / Mobile / Voice)
    decides how to present this interaction.
    """
    group_id: str = Field(description="Action Group identifier.")
    person: str = Field(description="Person requiring user confirmation.")
    interaction_type: HITLInteractionType = Field(description="Type of interaction required.")
    reason: HITLReason = Field(description="Reason why human input is required.")
    options: List[HITLOption] = Field(description="Available role options.")

class PersonRoleHITLResponse(BaseModel):
    """
    User response returned by the UI after
    selecting one of the presented options.
    """
    group_id: str = Field(description="Action Group identifier.")
    confirmed: bool | None = Field(default=None, description="User confirmation for CONFIRMATION interactions.")
    selected_option: int | None = Field(default=None, description="Selected option for SELECTION interactions.")

class ToolName(str, Enum):
    # Employee
    MANAGE_EMPLOYEE = "manage_employee"
    RECORD_EMPLOYEE_TRANSACTION = "record_employee_transaction"
    RECORD_ATTENDANCE = "record_attendance"

    # Customer / Sales
    MANAGE_CUSTOMER = "manage_customer"
    RECORD_SALE_TRANSACTION = "record_sale_transaction"
    RECORD_SALE_PAYMENT = "record_sale_payment"

    # Supplier
    MANAGE_SUPPLIER = "manage_supplier"
    RECORD_SUPPLIER_TRANSACTION = "record_supplier_transaction"
    RECORD_SUPPLIER_PAYMENT = "record_supplier_payment"

    RECORD_ADJUSTMENT = "record_adjustment"
    RECORD_WORK_LOG = "record_work_log"
    RECORD_MATERIAL_MOVEMENT = "record_material_movement"
    RECORD_EXPENSE = "record_expense"
    RECORD_EXPENSE_PAYMENT = "record_expense_payment"
    RECORD_PURCHASE = "record_purchase"
    RECORD_PURCHASE_PAYMENT = "record_purchase_payment"

    # Opening balance (Hisab-Kitab se pehle ka purana baaki / cash)
    RECORD_OPENING_BALANCE = "record_opening_balance"

    # Family (ghar ke log — family kharcha)
    RECORD_FAMILY_TRANSACTION = "record_family_transaction"


class TransactionType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    INTERNAL_MOVEMENT = "Internal Movement"
    DIRECT_SALE = "Direct Sale"
    UNRESOLVED = "Unresolved"

NEED_PERSON_BUNDLE = {
    PersonRole.EMPLOYEE: [
        ToolName.MANAGE_EMPLOYEE,
        ToolName.RECORD_EMPLOYEE_TRANSACTION,
        ToolName.RECORD_ATTENDANCE,
        ToolName.RECORD_OPENING_BALANCE,
    ],
    PersonRole.SUPPLIER: [
        ToolName.MANAGE_SUPPLIER,
        ToolName.RECORD_SUPPLIER_TRANSACTION,
        ToolName.RECORD_SUPPLIER_PAYMENT,
        ToolName.RECORD_OPENING_BALANCE,
    ],
    PersonRole.CUSTOMER: [
        ToolName.MANAGE_CUSTOMER,
        ToolName.RECORD_SALE_TRANSACTION,
        ToolName.RECORD_SALE_PAYMENT,
        ToolName.RECORD_OPENING_BALANCE,
    ],
    PersonRole.PROPERTY_OWNER: [
        ToolName.RECORD_PURCHASE,
        ToolName.RECORD_PURCHASE_PAYMENT,
    ],
    PersonRole.FAMILY_MEMBER: [
        ToolName.RECORD_FAMILY_TRANSACTION,
    ],
}

MATERIAL_MOVEMENT_BUNDLE = {
    TransactionType.IN: [
        ToolName.MANAGE_SUPPLIER,
        ToolName.RECORD_SUPPLIER_TRANSACTION,
        ToolName.RECORD_SUPPLIER_PAYMENT,
    ],
    TransactionType.OUT: [
        ToolName.MANAGE_CUSTOMER,
        ToolName.RECORD_SALE_TRANSACTION,
        ToolName.RECORD_SALE_PAYMENT,
    ],
    TransactionType.DIRECT_SALE: [
        ToolName.MANAGE_SUPPLIER,
        ToolName.MANAGE_CUSTOMER,
        ToolName.RECORD_SUPPLIER_TRANSACTION,
        ToolName.RECORD_SALE_TRANSACTION,
        ToolName.RECORD_SUPPLIER_PAYMENT,
        ToolName.RECORD_SALE_PAYMENT,
    ],
    TransactionType.INTERNAL_MOVEMENT: [
        ToolName.RECORD_MATERIAL_MOVEMENT,
    ],
    TransactionType.UNRESOLVED: [
        ToolName.RECORD_ADJUSTMENT,
    ],
}

STANDALONE_BUNDLE = [
    ToolName.RECORD_EXPENSE,
    ToolName.RECORD_EXPENSE_PAYMENT,
    ToolName.RECORD_PURCHASE,
    ToolName.RECORD_PURCHASE_PAYMENT,
    ToolName.RECORD_WORK_LOG,
    ToolName.RECORD_ADJUSTMENT,
    ToolName.RECORD_OPENING_BALANCE,   # shuru ka cash ("galle mein 40000 tha")
    ToolName.RECORD_FAMILY_TRANSACTION,  # bina naam ka ghar ka kharcha → member "Ghar"
]

# -- material movement schemas

class MaterialMovementInput(BaseModel):
    """
    Input provided to the Material Movement Node.
    Represents exactly one Action Group with record_type = MATERIAL_MOVEMENT.
    """
    group_id: str = Field(description="Unique Action Group identifier.")
    source: str | None = Field(default=None, description="Source location as extracted from identity_key. None/empty if missing from the statement.")
    destination: str | None = Field(default=None, description="Destination location as extracted from identity_key. None/empty if missing from the statement.")
    actions: List[Action] = Field(description="All actions belonging to this Material Movement group.")

class MaterialMovementHITLReason(str, Enum):
    MISSING_FIELD = "MISSING_FIELD"
    LOCATION_TYPE_CONFIRMATION = "LOCATION_TYPE_CONFIRMATION"

class LocationTypeOption(BaseModel):
    option_id: int = Field(description="Unique option identifier.")
    location_type: MovementEntityType = Field(description="Candidate entity type — storage, site, customer, or supplier.")

class MaterialMovementHITLRequest(BaseModel):
    """
    Structured request sent to the UI layer for Material Movement resolution.
    Covers two scenarios via `reason`:
    - MISSING_FIELD: source or destination was not stated in the action.
    - LOCATION_TYPE_CONFIRMATION: the name is known, but its entity type
      (storage/site/customer/supplier) is not yet in the unified
      MovementEntityLookup table.
    """
    group_id: str = Field(description="Action Group identifier.")
    reason: MaterialMovementHITLReason = Field(description="Why human input is required.")
    missing_field: str | None = Field(default=None, description="Which field is missing: 'source' or 'destination'. Set only when reason=MISSING_FIELD.")
    location_name: str | None = Field(default=None, description="The location name needing type confirmation. Set only when reason=LOCATION_TYPE_CONFIRMATION.")
    options: List[LocationTypeOption] = Field(default_factory=list, description="Available location type options. Populated only when reason=LOCATION_TYPE_CONFIRMATION.")
    suggestions: List[str] = Field(default_factory=list, description="MISSING_FIELD: known storage locations to offer as quick choices (plus 'pata nahi').")

class MaterialMovementHITLResponse(BaseModel):
    """
    User response returned by the UI.
    """
    group_id: str = Field(description="Action Group identifier.")
    provided_value: str | None = Field(default=None, description="The missing source/destination name, provided by the user. Set only when responding to MISSING_FIELD.")
    selected_option: int | None = Field(default=None, description="Selected location type option_id. Set only when responding to LOCATION_TYPE_CONFIRMATION.")

class MaterialMovementResult(BaseModel):
    """
    Output of the Material Movement Node after source and destination
    have been resolved as far as possible (name known + entity type
    known, or left None if the user skipped confirmation).
    Passed forward to the Transaction Classifier.
    """
    group_id: str = Field(description="Action Group identifier.")
    source: str | None = Field(default=None, description="Resolved source name. None if user skipped providing it.")
    source_type: MovementEntityType | None = Field(default=None, description="Resolved source entity type — storage, site, customer, or supplier. None if unknown/skipped.")
    destination: str | None = Field(default=None, description="Resolved destination name. None if user skipped providing it.")
    destination_type: MovementEntityType | None = Field(default=None, description="Resolved destination entity type. None if unknown/skipped.")
    actions: List[Action] = Field(description="All actions belonging to this group, carried forward.")


class TransactionClassifierResult(BaseModel):
    group_id: str
    transaction_type: TransactionType
    source: str | None
    destination: str | None
    note: str | None = None





class ActionToolDecision(BaseModel):
    action_index: int = Field(ge=0, description="Zero-based index of the action inside the group.")
    selected_tools: List[ToolName] = Field(description="Tools applicable ONLY to this action.")

class ToolDecisionResult(BaseModel):
    group_id: str = Field(description="Unique Action Group identifier.")
    action_decisions: List[ActionToolDecision] = Field(description="Tool decisions for each action in this group.")

class ToolDecisionInput(BaseModel):
    """
    Input provided to the Tool Decision LLM.
    Represents exactly one Action Group.
    """
    group_id: str = Field(description="Unique Action Group identifier.")
    actions: List[Action] = Field(description="Actions belonging to this Action Group.")
    person_role: PersonRole | None = Field(default=None,description="Resolved person role after HITL. None if no person is involved.")
    available_tools: List[ToolName] = Field(description="Tools available for selection.")
    transaction_type: TransactionType | None = Field(default=None, description="Resolved transaction type for Material Movement groups. None otherwise.")
    record_type: RecordType = Field(description="Which branch this group came from — used to select the tool bundle when neither person_role nor transaction_type applies (e.g. Standalone Transaction).")


class ToolArgumentResult(BaseModel):
    """
    Structured arguments extracted for one selected tool.
    Represents one tool execution request.
    """
    group_id: str = Field(description="Action Group identifier.")
    action_index: int = Field(ge=0, description="Zero-based index of the action inside the group.")
    tool_name: ToolName = Field(description="Tool selected by the Tool Decision node.")
    arguments: Any = Field(description="Pydantic model containing the extracted arguments for the selected tool.")

class ToolArgumentExtractionResult(BaseModel):
    """
    Output of the Tool Argument Extraction Node.
    """
    results: List[ToolArgumentResult] = Field(description="Structured arguments extracted for all selected tools.")


class MissingArgument(BaseModel):
    """
    One missing required argument.
    """
    field_name: str = Field(description="Missing required field.")
    description: str = Field(description="Human readable description of the field.")

class ToolArgumentHITLRequest(BaseModel):
    """
    Request sent to UI for Tool Argument HITL.
    """
    group_id: str = Field(description="Action Group identifier.")
    tool_name: ToolName = Field(description="Tool being confirmed.")
    arguments: Any = Field(description="Current extracted arguments.")
    missing_arguments: List[MissingArgument] = Field(description="Required fields still missing.")

class ToolArgumentHITLResponse(BaseModel):
    """
    Response returned by UI.
    """
    group_id: str = Field(description="Action Group identifier.")
    updated_statement: str | None = Field(default=None, description="Complete updated statement OR only missing field.")
    confirmed: bool | None = Field(default=None, description="Final user confirmation.")


class FinalConfirmationRequest(BaseModel):
    tool_name: ToolName
    action_index: int
    arguments: dict

class FinalConfirmationResponse(BaseModel):
    confirmed: bool


class ResolvedActionDate(BaseModel):
    """
    Date Resolution LLM ka output for one existing action.
    """
    group_id: str = Field(description="Existing Action Group ID.")
    action_index: int = Field(ge=0, description="Zero-based index of the action inside the group.")
    date: str = Field(description="Final resolved date in YYYY-MM-DD format.")

class DateResolutionResult(BaseModel):
    """
    Output of the Date Resolution LLM.
    Contains ONLY date decisions.
    The existing GroupedIntent structure is never returned or modified
    by the LLM.
    """
    resolved_dates: List[ResolvedActionDate] = Field(description="Final date for every existing action.")


    
class CorrectionDateResult(BaseModel):
    date: str | None = Field(
        default=None,
        description="YYYY-MM-DD if the text states a date or relative date, else null.",
    )

class CorrectionDateHITLRequest(BaseModel):
    group_id: str
    text: str = Field(description="The correction sentence the user gave.")
    retry: bool = Field(default=False, description="True if the previous answer could not be parsed.")

class CorrectionDateHITLResponse(BaseModel):
    group_id: str
    answer: str


class CorrectionCategoryOption(BaseModel):
    option_id: int
    category: str = Field(description="Value matching audit_log.category")
    label: str

class CorrectionCategoryHITLRequest(BaseModel):
    group_id: str
    options: List[CorrectionCategoryOption]

class CorrectionCategoryHITLResponse(BaseModel):
    group_id: str
    selected_option: int | None = None
    cancelled: bool = False

class CorrectionRangeOption(BaseModel):
    option_id: int
    label: str
    days: int   # 0 = cancel

class CorrectionRangeHITLRequest(BaseModel):
    group_id: str
    options: List[CorrectionRangeOption]

class CorrectionRangeHITLResponse(BaseModel):
    group_id: str
    selected_option: int | None = None
    cancelled: bool = False


class CorrectionDetailHITLRequest(BaseModel):
    group_id: str
    days: int

class CorrectionDetailHITLResponse(BaseModel):
    group_id: str
    answer: str

class CorrectionDetailResult(BaseModel):
    date: str | None = Field(default=None, description="YYYY-MM-DD if the text states a date, else null.")
    name: str | None = Field(default=None, description="Person/party name mentioned, else null.")

class CorrectionMatchOption(BaseModel):
    option_id: int
    entry_id: int = Field(description="audit_log.id (andar ka)")
    voucher: str = Field(description="User ko dikhne wala number, jaise 28-1")
    date: str
    party: str
    type_label: str
    debit: float | None = None
    credit: float | None = None
    note: str = "-"
    statement: str

class CorrectionMatchHITLRequest(BaseModel):
    group_id: str
    category: str = ""
    options: List[CorrectionMatchOption]
    total: int = Field(description="Total matches found (list may be capped).")
    name_dropped: bool = False

class CorrectionMatchHITLResponse(BaseModel):
    group_id: str
    selected_option: int | None = None
    cancelled: bool = False




class CorrectionConfirmHITLRequest(BaseModel):
    group_id: str
    date: str
    party: str
    type_label: str
    debit: float | None = None
    credit: float | None = None
    note: str = "-"

class CorrectionConfirmHITLResponse(BaseModel):
    group_id: str
    confirmed: bool


class CorrectionActionOption(BaseModel):
    option_id: int
    label: str

class CorrectionActionHITLRequest(BaseModel):
    group_id: str
    options: List[CorrectionActionOption]

class CorrectionActionHITLResponse(BaseModel):
    group_id: str
    selected_option: int | None = None
    cancelled: bool = False


class CorrectionStatementHITLRequest(BaseModel):
    group_id: str
    old_statement: str

class CorrectionStatementHITLResponse(BaseModel):
    group_id: str
    answer: str


# =====================================================================
# --- Reporting Phase
# =====================================================================

class ReportParseResult(BaseModel):
    kind: str | None = Field(default=None, description=(
        "overall | person | purchase | expense | cash_flow | work_log | material_movement, or null"))
    person_name: str | None = Field(default=None, description="Named person/party, else null.")
    person_role: str | None = Field(default=None, description="employee | customer | supplier | family, only if stated.")
    date_from: str | None = Field(default=None, description="YYYY-MM-DD if a duration/date is stated, else null.")
    date_to: str | None = Field(default=None, description="YYYY-MM-DD if a duration/date is stated, else null.")
    language: str | None = Field(default=None, description="hi | hg | en if the user asks for a language, else null.")


class ReportRangeResult(BaseModel):
    date_from: str | None = Field(default=None, description="YYYY-MM-DD or null")
    date_to: str | None = Field(default=None, description="YYYY-MM-DD or null")


class ReportOption(BaseModel):
    option_id: int
    label: str


class ReportHITLRequest(BaseModel):
    """Report ka har sawaal — ek hi shape: question + numbered options (+ text allowed?)."""
    step: str = Field(description="kind | role | name | range | language")
    question: str
    options: List[ReportOption] = Field(default_factory=list)
    allow_text: bool = False
    hint: str | None = None
    retry: bool = False


class ReportHITLResponse(BaseModel):
    selected_option: int | None = None
    answer: str | None = None
    cancelled: bool = False
