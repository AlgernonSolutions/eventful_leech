(
    sam validate --profile dev
) && (
    sam build --profile dev --use-container -b .aws-sam\build
) && (
    sam package ^
        --profile dev ^
        --s3-bucket algernonsolutions-layer-dev ^
        --template-file .aws-sam\build\template.yaml ^
        --output-template-file .aws-sam\build\templated.yaml
) && (
    aws cloudformation deploy ^
        --profile dev ^
        --template .aws-sam\build\templated.yaml ^
        --stack-name leech-dev-2 ^
        --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM ^
        --force-upload ^
        --parameter-overrides ^
            StorageBucketName=algernonsolutions-leech-dev ^
            DataGqlEndpoint=jlgmowxwofe33pdekndakyzx4i.appsync-api.us-east-1.amazonaws.com ^
            EncounterBucketName=algernonsolutions-encounters-dev
)