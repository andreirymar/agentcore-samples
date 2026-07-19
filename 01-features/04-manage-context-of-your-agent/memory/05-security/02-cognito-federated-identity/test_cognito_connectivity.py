#!/usr/bin/env python3

import argparse
import os

import boto3


def parse_args():
    parser = argparse.ArgumentParser(
        description="Smoke test Cognito User Pool auth and Identity Pool credential exchange."
    )
    parser.add_argument("--region", default=os.getenv("AWS_REGION") or boto3.Session().region_name or "ca-central-1")
    parser.add_argument("--user-pool-id", default=os.getenv("COGNITO_USER_POOL_ID"))
    parser.add_argument("--client-id", default=os.getenv("COGNITO_CLIENT_ID"))
    parser.add_argument("--identity-pool-id", default=os.getenv("COGNITO_IDENTITY_POOL_ID"))
    parser.add_argument("--username", default=os.getenv("COGNITO_TEST_USERNAME", "testuser1"))
    parser.add_argument("--password", default=os.getenv("COGNITO_TEST_PASSWORD", "MyPassword123!"))
    return parser.parse_args()


def require(value, name):
    if not value:
        raise SystemExit(f"Missing required value for {name}. Pass --{name.replace('_', '-')} or set the env var.")
    return value


def main():
    args = parse_args()

    region = args.region
    user_pool_id = require(args.user_pool_id, "user_pool_id")
    client_id = require(args.client_id, "client_id")
    identity_pool_id = require(args.identity_pool_id, "identity_pool_id")

    cognito_idp = boto3.client("cognito-idp", region_name=region)
    cognito_identity = boto3.client("cognito-identity", region_name=region)

    print(f"Region: {region}")
    print(f"User Pool ID: {user_pool_id}")
    print(f"Client ID: {client_id}")
    print(f"Identity Pool ID: {identity_pool_id}")
    print(f"Username: {args.username}")

    auth_response = cognito_idp.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": args.username, "PASSWORD": args.password},
    )
    access_token = auth_response["AuthenticationResult"]["AccessToken"]
    id_token = auth_response["AuthenticationResult"]["IdToken"]
    print("User Pool auth OK")
    print(f"Access token prefix: {access_token[:20]}...")

    provider_name = f"cognito-idp.{region}.amazonaws.com/{user_pool_id}"
    get_id_response = cognito_identity.get_id(
        IdentityPoolId=identity_pool_id,
        Logins={provider_name: id_token},
    )
    identity_id = get_id_response["IdentityId"]
    print(f"Identity Pool get_id OK: {identity_id}")

    credentials_response = cognito_identity.get_credentials_for_identity(
        IdentityId=identity_id,
        Logins={provider_name: id_token},
    )
    credentials = credentials_response["Credentials"]
    print("Federated credentials OK")
    print(f"AccessKeyId prefix: {credentials['AccessKeyId'][:12]}")
    print(f"Expiration: {credentials['Expiration']}")


if __name__ == "__main__":
    main()