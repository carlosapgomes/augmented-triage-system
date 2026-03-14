# dashboard-pwa-installability Specification

## Purpose

TBD - created by archiving change dashboard-pwa-mobile-installable. Update Purpose after archive.

## Requirements

### Requirement: Dashboard SHALL Expose Installability Metadata And Assets

The system SHALL expose all required PWA metadata and static assets so supported mobile browsers can recognize the dashboard as an installable web app.

#### Scenario: Browser loads dashboard shell metadata

- **WHEN** a user opens dashboard web pages rendered from the shared base template
- **THEN** the HTML MUST include a reference to the web app manifest
- **AND** the HTML MUST include PWA/mobile metadata required for standalone launch behavior

#### Scenario: Browser fetches web app manifest

- **WHEN** a browser requests the manifest resource
- **THEN** the system MUST return a valid web app manifest document
- **AND** the manifest MUST declare `short_name` as `CHD`, `start_url` as `/dashboard/cases`, and `display` as `standalone`
- **AND** the manifest MUST reference install icons for Android and iOS usage

### Requirement: Dashboard Icon Set SHALL Follow CHD Visual Identity

The system SHALL provide an app icon set with square composition and CHD textual branding aligned with the existing dashboard header visual style.

#### Scenario: Browser requests installation icons

- **WHEN** a browser requests icon assets referenced by the manifest and Apple mobile metadata
- **THEN** the system MUST return valid icon files for required sizes used by installation flows
- **AND** icon composition MUST preserve `CHD` in prominent uppercase text with `dashboard` in smaller text below
- **AND** icon colors MUST follow the dashboard header palette/gradient family

### Requirement: Service Worker SHALL Be Online-Only

The system SHALL register a service worker for installability support without adding offline caching behavior for dashboard content.

#### Scenario: Connected user navigates with service worker active

- **WHEN** a user navigates dashboard pages with network connectivity
- **THEN** requests MUST be fulfilled from network responses
- **AND** the service worker MUST NOT serve stale cached dashboard HTML as authoritative content

#### Scenario: User loses network connectivity

- **WHEN** a user requests dashboard content while offline
- **THEN** the system MUST NOT present offline fallback as supported feature behavior
- **AND** the request result MUST reflect normal network failure semantics
