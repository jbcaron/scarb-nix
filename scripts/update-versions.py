import requests
import json
import re
import logging
from pathlib import Path
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('update-versions.log')
    ]
)
logger = logging.getLogger('scarb-updater')

def fetch_releases():
    """Fetch all releases from GitHub API"""
    api_url = "https://api.github.com/repos/software-mansion/scarb/releases"
    logger.info(f"Fetching releases from {api_url}")
    
    headers = {}
    # if github_token := os.environ.get("GITHUB_TOKEN"):
    #     headers["Authorization"] = f"token {github_token}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        releases = response.json()
        logger.info(f"Successfully fetched {len(releases)} releases")
        return releases
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch releases: {e}")
        raise

def get_asset_info(release):
    """Extract relevant asset information from a release"""
    assets = {}
    for asset in release['assets']:
        assets[asset['name']] = {
            "url": asset['browser_download_url'],
            "size": asset['size'],
            "download_count": asset['download_count'],
            "created_at": asset['created_at'],
            "updated_at": asset['updated_at']
        }
    return assets

def parse_checksums(text, version_tag):
    """Parse the checksums file content"""
    logger.debug(f"Parsing checksums for version {version_tag}")
    
    checksums = {}
    for line in text.split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            checksum, filename = parts
            match = re.search(r'scarb-v[\d\.]+-([\w-]+)\.(tar\.gz|zip)', filename)
            if match:
                platform = match.group(1)
                checksums[platform] = checksum
                logger.debug(f"Found checksum for platform {platform}: {checksum[:8]}...")

    logger.info(f"Parsed {len(checksums)} platform checksums for version {version_tag}")
    return checksums

def get_version_checksums(version_tag):
    """Get checksums for a specific version"""
    checksums_url = f"https://github.com/software-mansion/scarb/releases/download/{version_tag}/checksums.sha256"
    logger.info(f"Fetching checksums from {checksums_url}")
    
    try:
        response = requests.get(checksums_url)
        response.raise_for_status()
        checksums = parse_checksums(response.text, version_tag)
        return checksums
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch checksums for {version_tag}: {e}")
        return None

def process_changelog(body):
    """Process and clean up the changelog text"""
    if not body:
        return None
    
    # Remove any HTML comments
    body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
    
    # Clean up whitespace
    body = '\n'.join(line.rstrip() for line in body.splitlines())
    body = body.strip()
    
    return body if body else None

def load_current_versions(versions_file):
    """Load current versions from file if it exists"""
    try:
        if versions_file.exists():
            with open(versions_file) as f:
                logger.info(f"Loading existing versions from {versions_file}")
                return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Error reading existing versions file: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error reading versions file: {e}")
    
    logger.info("No existing versions found or file is invalid")
    return {}

def update_versions_file(versions_file):
    """Update the versions.json file with all releases"""
    logger.info("Starting version update process")
    
    # Load current versions
    current_versions = load_current_versions(versions_file)
    current_count = len(current_versions)
    logger.info(f"Found {current_count} existing versions")
    
    try:
        releases = fetch_releases()
        versions = {}
        processed_count = 0
        skipped_count = 0
        
        for release in releases:
            version = release['tag_name'].lstrip('v')
            
            # Skip drafts
            if release['draft']:
                logger.debug(f"Skipping draft version {version}")
                skipped_count += 1
                continue
            
            # If we already have this version, let's check if the metadata needs to be updated
            if version in current_versions:
                existing_date = current_versions[version]['metadata']['releaseDate']
                current_date = release['published_at']
                if existing_date == current_date:
                    logger.debug(f"Version {version} already up to date, skipping")
                    versions[version] = current_versions[version]
                    processed_count += 1
                    continue
                else:
                    logger.info(f"Updating metadata for version {version}")

            logger.info(f"Processing version: {version}")
            checksums = get_version_checksums(release['tag_name'])
            
            if checksums:
                versions[version] = {
                    "hashes": checksums,
                    "metadata": {
                        "releaseDate": release['published_at'],
                        "prerelease": release['prerelease'],
                        "draft": release['draft'],
                        "changelog": process_changelog(release['body']),
                        "downloadCount": sum(asset['download_count'] for asset in release['assets']),
                        "assets": get_asset_info(release)
                    }
                }
                processed_count += 1
                logger.info(f"Successfully processed version {version}")
            else:
                logger.warning(f"Skipping version {version} due to missing checksums")
                skipped_count += 1
        
        # Create versions directory if it doesn't exist
        versions_dir = Path("versions")
        versions_dir.mkdir(exist_ok=True)
        
        # Backup existing file if it exists
        if versions_file.exists():
            backup_path = versions_file.with_suffix(f'.json.bak-{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            versions_file.rename(backup_path)
            logger.info(f"Backed up existing versions file to {backup_path}")
        
        # Write updated versions to file
        with open(versions_file, 'w') as f:
            json.dump(versions, f, indent=2, sort_keys=True)
        
        logger.info(f"Successfully updated versions file:")
        logger.info(f"- Processed: {processed_count} versions")
        logger.info(f"- New versions: {processed_count - current_count}")
        logger.info(f"- Skipped: {skipped_count} versions")
        
    except Exception as e:
        logger.error(f"Error updating versions: {e}", exc_info=True)
        raise

def main():
    versions_file = Path("versions/versions.json")
    logger.info("=== Starting Scarb versions update ===")
    logger.info(f"Target file: {versions_file}")
    
    try:
        update_versions_file(versions_file)
        logger.info("=== Update completed successfully ===")
    except Exception as e:
        logger.error("=== Update failed ===")
        sys.exit(1)

if __name__ == "__main__":
    main()