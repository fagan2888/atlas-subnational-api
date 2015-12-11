set -e

if [ -z $BUCKETNAME ]; then
    echo "You need to set BUCKETNAME=blah to say which s3 bucket to upload to e.g. s3://blah-bucket-prod";
    exit 1;
fi

if [ -z $PROFILENAME ]; then
    echo "You need to set PROFILENAME=blah to refer to the awscli credentials you want to use.";
    exit 1;
fi

if [ -z $SOURCE ]; then
    echo "You need to set SOURCE=blah to tell me what folder to copy.";
    exit 1;
fi

# Generate new folder name: yyyy-mm-dd-git_tag
FOLDERNAME=$(./scripts/get_version_string.sh)

# Upload generated files
aws s3 sync $SOURCE $BUCKETNAME/generated/$FOLDERNAME/ --content-encoding=gzip --profile $PROFILENAME

# Copy in manually uploaded custom files to complete downloads
aws s3 sync $BUCKETNAME/custom/ $BUCKETNAME/generated/$FOLDERNAME/ --profile $PROFILENAME

# Update the production folder to what we just uploaded and make it public
aws s3 sync $BUCKETNAME/generated/$FOLDERNAME/ $BUCKETNAME/production/ --acl=public-read --delete --profile $PROFILENAME