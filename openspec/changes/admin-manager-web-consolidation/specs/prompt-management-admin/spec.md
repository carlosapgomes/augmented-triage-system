# prompt-management-admin Specification

## MODIFIED Requirements

### Requirement: Prompt Management SHALL Have An Authenticated HTML Admin Surface

The system SHALL provide the prompt-management HTML surface inside the consolidated Django administrative area for `admin` users.

#### Scenario: Admin opens prompt management page in the consolidated Django app

- **WHEN** an authenticated `admin` requests the prompt-management page inside the Django admin area
- **THEN** the system MUST render prompt names, versions, active state, and activation controls

### Requirement: Reader SHALL Have Read-Only Monitoring Access

The system SHALL restrict prompt-management operations to `admin` and MUST reject access attempts by non-admin supervisory roles as well.

#### Scenario: Manager requests prompt admin page

- **WHEN** an authenticated `manager` requests the prompt-management HTML page
- **THEN** the system MUST reject access with authorization failure
