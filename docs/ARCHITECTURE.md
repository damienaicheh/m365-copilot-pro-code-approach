# Architecture

This project is an M365 Agent Application built with Python, the M365 Agents SDK and the
Microsoft Agent Framework, deployable to Azure using the Azure Developer CLI (`azd`). It
demonstrates how to build a secure enterprise agent that surfaces natively in Microsoft 365
Copilot and Teams, with per-user document access control through Azure AI Search and Entra
security groups.

For the authentication flows (Bot Service ↔ agent code, user SSO, per-user Search token),
see [AUTHENTICATION.md](./AUTHENTICATION.md).

## High-level architecture

![High-level architecture: Teams / M365 Copilot, Production and Development bot identities, APIM (validate-jwt), Orchestrator Agent / Local agent, AI Search and Microsoft Foundry](./images/architecture-overview.png)

<!-- Diagram source: docs/mermaids/architecture-overview.mmd (regenerate the PNG with mermaid-cli) -->

## Detailed sequence diagram

```mermaid
sequenceDiagram
    autonumber
    %% Groups
    box rgb(227, 242, 253) User
        participant U as Copilot / Teams User
    end

    box rgb(237, 231, 246) Microsoft 365 / Teams
        participant M as Microsoft 365 Copilot & Teams
    end

    box rgb(255, 243, 224) Azure Bot Platform
        participant B as Azure Bot Service
        participant T as Bot Token Service
    end

    box rgb(232, 245, 233) Custom Engine Agent - Azure Resource Group
        participant AP as Azure APIM (Optional)
        participant P as App Service / Agent App (M365 Agents SDK)
    end

    box rgb(252, 228, 236) Retrieval & Reasoning
        participant S as Azure AI Search
        participant G as Microsoft Graph
        participant F as Microsoft Foundry (FoundryChatClient)
    end

    %% Inbound Message Flow
    U->>M: User prompt<br/>(e.g., "Create a report")
    M->>B: Send activity
    B->>AP: POST /bot/api/messages<br/>Authorization: Bearer BF_JWT
    AP->>AP: validate-jwt<br/>iss=api.botframework.com<br/>aud={bot-app-id}
    AP->>P: Forward activity to /api/messages

    %% Search Token Exchange Flow
    rect rgb(245, 245, 245)
        Note over P,T: auth_handlers=["SEARCH"]
        P->>B: get_token("SEARCH")
        B->>M: Request SSO token (silent/consent)
        M->>U: Silent sign-in or consent prompt
        B->>T: Token exchange for search_access_token
        T-->>P: Search token<br/>(aud=search.azure.com)
    end

    %% Per-User Retrieval Flow
    rect rgb(245, 245, 245)
        Note over P,G: Native ACL filtering in AI Search
        P->>S: Query + x-ms-query-source-authorization
        S->>G: Resolve user group memberships
        G-->>S: User groups
        S-->>P: ACL-filtered documents
    end

    %% Agent + LLM Flow
    rect rgb(245, 245, 245)
        Note over P,F: Orchestration and streaming response
        P->>F: FoundryChatClient.run<br/>question + filtered docs
        F-->>P: Streaming response chunks
    end

    %% Outbound Reply Flow (direct, not via APIM)
    P-->>B: Reply activities (Bot Connector path)
    B-->>M: Stream content
    M-->>U: Display result progressively
```

## Production vs Development / Debug configuration

The application can run in two modes:

- **Production** — deployed to Azure, real SSO + per-user ACLs.
- **Development / Debug** — local Bot Service + Dev tunnel, for breakpoints and fast iteration.

Each mode has its **own** bot identity **and its own SSO app registration** (federated
credentials, user sign-in, per-user Search ACLs); they only share the **same APIM gateway**.
What changes is **where the agent runs** and **which bot identity** fronts it. The
development mode adds a dedicated, single-tenant bot identity because a laptop cannot use
the managed identity that the deployed app relies on.

| Aspect | Production | Development / Debug |
|---|---|---|
| Where the agent runs | Azure App Service (Linux) | Your machine, exposed through a dev tunnel |
| Bot identity | User-assigned managed identity | Dedicated single-tenant app registration |
| How the bot proves its identity to Bot Service | Managed identity (no secret) | Client secret (minted locally) |
| Azure Bot Service resource | Production bot | Separate local bot |
| Messaging endpoint chain | APIM → App Service | APIM → dev tunnel → local agent |
| Teams manifest bot id | Production bot identity | Local bot app registration |
| User sign-in (SSO) app | Production SSO app (federated credentials) | Dedicated local SSO app (federated credentials) |
| Per-user Search token | OAuth connection on the production bot (production SSO app) | OAuth connection on the local bot (local SSO app) |
| Microsoft Foundry access | Managed identity | Your developer sign-in (`az login`) |
| Typical use | Real tenant rollout | Breakpoints and fast iteration |

> The Teams manifest's bot id must always match the Microsoft App ID configured on the
> Azure Bot Service it targets. In production that is the managed identity; in development
> it is the local single-tenant bot app registration. The SSO entry in the manifest
> (`webApplicationInfo`) points to the **production** SSO app in production and to the
> **dedicated local** SSO app in development — each environment is self-contained.

### Production architecture

![Production architecture: Teams / M365 Copilot to Azure Bot Service, APIM (validate-jwt), Orchestrator Agent, AI Search and Microsoft Foundry](./images/architecture-production.png)

<!-- Diagram source: docs/mermaids/architecture-production.mmd (regenerate the PNG with mermaid-cli) -->

### Development / Debug architecture

![Development architecture: Teams / M365 Copilot to Local Bot Service, APIM, Dev tunnel, Local agent, AI Search and Microsoft Foundry](./images/architecture-development.png)

<!-- Diagram source: docs/mermaids/architecture-development.mmd (regenerate the PNG with mermaid-cli) -->
