# Cognito federated-identity isolation

Exchange a Cognito ID token for short-lived AWS credentials via a Cognito Identity Pool, then call AgentCore Memory with those per-user credentials. The user's `identityId` is the `actorId`, and the Identity Pool's authenticated role governs what each user can do — no application-layer `actorId` enforcement required.

Compared to [`../01-iam-scoped-access/`](../01-iam-scoped-access/), this approach binds identity to the credential itself: there is no shared service role that could be tricked into reading another user's data.

## What you learn

- Set up a Cognito User Pool + Identity Pool with `AssumeRoleWithWebIdentity`
- Exchange a Cognito ID token for temporary AWS credentials at invocation time
- Call AgentCore Memory using those credentials so identity is enforced by IAM, not by app code
- Verify isolation — each user's credentials can only operate on their own `identityId` namespace

## Architecture

![Federated identity](./architecture.png)

The user authenticates against the Cognito User Pool, receives a JWT, exchanges it at the Identity Pool for short-lived STS credentials, and the agent calls `bedrock-agentcore` with those credentials. The Identity Pool authenticated role's policy is conditioned on `${cognito-identity.amazonaws.com:sub}`, so credentials issued for user A cannot read user B's events.

## Run

```bash
cd 01-features/04-manage-context-of-your-agent/memory/05-security/02-cognito-federated-identity
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export AWS_REGION=ca-central-1
python runtime_memory_federated_identity_integration.py
```

The script provisions the User Pool, the Identity Pool, the authenticated role, and the agent runtime; then signs in as two different users to verify per-user credential isolation.

### Standalone Cognito smoke test

If you want to verify Cognito connectivity without running the full runtime deployment, use the
standalone smoke test after you have a User Pool, App Client, and Identity Pool.

The `--user-pool-id`, `--client-id`, and `--identity-pool-id` must come from the same Cognito
setup. If you mix a User Pool or App Client from another tutorial or environment, Cognito Identity
returns `NotAuthorizedException: Token is not from a supported provider of this identity pool`.

For resources created by this sample, the test users are:

- `testuser1` / `MyPassword123!`
- `testuser2` / `MyPassword456!`

```bash
export AWS_REGION=ca-central-1
export AWS_CA_BUNDLE=/tmp/aws-ca-bundle-netskope-full.pem
python test_cognito_connectivity.py \
	--user-pool-id <user-pool-id> \
	--client-id <app-client-id> \
	--identity-pool-id <identity-pool-id>
```

Expected output:

- `User Pool auth OK`
- `Identity Pool get_id OK: ...`
- `Federated credentials OK`

### Troubleshooting: SSL certificate verify failed

If you see an error like `CERTIFICATE_VERIFY_FAILED` when calling IAM endpoints, your environment likely uses a proxy or custom root CA.

1. Install project dependencies from this folder first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. If your organization provides a custom root certificate, configure boto3/requests to trust it:

```bash
export AWS_CA_BUNDLE="/path/to/corporate-root-ca.pem"
export REQUESTS_CA_BUNDLE="/path/to/corporate-root-ca.pem"
export AWS_REGION=ca-central-1
```

Optional: make this persistent for new terminal sessions:

```bash
cat >> ~/.zshrc <<'EOF'
# AgentCore samples: trust local corporate CA bundle when present
if [ -f /path/to/corporate-root-ca.pem ]; then
	export AWS_CA_BUNDLE=/path/to/corporate-root-ca.pem
	export REQUESTS_CA_BUNDLE=/path/to/corporate-root-ca.pem
fi
EOF
source ~/.zshrc
```

3. Re-run the script:

```bash
python runtime_memory_federated_identity_integration.py
```

If you see a `uv` error like `Failed to fetch https://pypi.org/... UnknownIssuer` during the
deployment packaging step, update to the latest version of this sample. The packaging command in
this sample now uses `uv --system-certs` so `uv` trusts the system certificate store in corporate
proxy environments.

## When to prefer this over IAM-scoped roles

| Use federated identity when… | Stay with IAM-scoped roles when… |
|---|---|
| You can't trust application code to set `actorId` correctly | A single trusted runtime is the only memory caller |
| Compliance requires user-bound credentials in CloudTrail | Operational simplicity matters more than per-call attribution |
| Browser/mobile clients call memory directly | Only server-side code touches memory |

## Best practices

- **Use the Cognito Identity `identityId`, not the User Pool `sub`,** as the `actorId` in this pattern — that's what the Identity Pool policy variables resolve to.
- **Set short token lifetimes** on the User Pool — federated credentials inherit that lifetime, capping blast radius if a token leaks.
- **Don't long-cache STS credentials** at the client. Re-exchange on each session start.
- **Audit `kms:Decrypt` and `bedrock-agentcore:*` in CloudTrail** — each call carries the federated `identityId` for clean attribution.
- **Combine with KMS for tenant isolation** when contracts require key revocation per tenant. See [`../03-kms-encryption/`](../03-kms-encryption/).

## Where to go next

- Customer-managed KMS keys: [`../03-kms-encryption/`](../03-kms-encryption/)
- Namespace organisation that pairs with these conditions: [`../../02-long-term-memory/04-namespaces/`](../../02-long-term-memory/04-namespaces/)
