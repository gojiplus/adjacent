import os
import requests
import base64
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REPO = os.getenv("GITHUB_REPOSITORY")  # e.g., 'soodoku/bloomjoin'
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}"
}

def get_topics(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    r = requests.get(url, headers=HEADERS)
    return r.json().get("names", []) if r.status_code == 200 else []

def get_user_repos(owner):
    url = f"https://api.github.com/users/{owner}/repos?per_page=100&type=owner"
    repos = []
    while url:
        r = requests.get(url, headers=HEADERS)
        repos.extend(r.json())
        link_header = r.headers.get('Link', '')
        url = None
        for link in link_header.split(','):
            if 'rel="next"' in link:
                url = link.split(';')[0].strip('<>')
                break
    return repos

def get_readme_content(owner, repo):
    """Fetch README content from a repository"""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        content = r.json().get("content", "")
        if content:
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                # Clean the markdown content
                cleaned = clean_markdown(decoded)
                return cleaned
            except Exception as e:
                print(f"Error decoding README for {owner}/{repo}: {e}")
    return ""

def clean_markdown(text):
    """Clean markdown content to improve text similarity comparison"""
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`.*?`', '', text)
    # Remove links but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove headers
    text = re.sub(r'#+\s+', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove images
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compute_readme_similarity(text1, text2):
    """Compute cosine similarity between two README texts using TF-IDF"""
    if not text1 or not text2:
        return 0.0
    
    # Create a TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words='english')
    
    try:
        # Calculate TF-IDF matrix
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    except Exception as e:
        print(f"Error computing similarity: {e}")
        return 0.0

def find_adjacent_by_topics(owner, repo_name, topics):
    """Find adjacent repositories based on common topics"""
    repos = get_user_repos(owner)
    related = []
    for r in repos:
        if r["name"].lower() == repo_name.lower():
            continue
        t = get_topics(r["owner"]["login"], r["name"])
        common = set(t) & set(topics)
        if common:
            related.append((r["full_name"], r.get("description", ""), list(common), len(common)/len(set(t) | set(topics))))
    return sorted(related, key=lambda x: -x[3])

def find_adjacent_by_readme(owner, repo_name, readme_content):
    """Find adjacent repositories based on README content similarity"""
    repos = get_user_repos(owner)
    related = []
    for r in repos:
        if r["name"].lower() == repo_name.lower():
            continue
        other_readme = get_readme_content(r["owner"]["login"], r["name"])
        similarity = compute_readme_similarity(readme_content, other_readme)
        if similarity > 0.1:  # Threshold for considering repositories as related
            related.append((r["full_name"], r.get("description", ""), [], similarity))
    return sorted(related, key=lambda x: -x[3])

def find_adjacent_combined(owner, repo_name, topics, readme_content, weight_topics=0.5):
    """Find adjacent repositories using a weighted combination of topics and README similarity"""
    repos = get_user_repos(owner)
    related = []
    
    # Check if we have topics and README content
    has_topics = len(topics) > 0
    has_readme = len(readme_content) > 0
    
    # Adjust weights if one source is missing
    effective_weight_topics = weight_topics
    if not has_topics:
        effective_weight_topics = 0
    if not has_readme:
        effective_weight_topics = 1
    
    # Collect similarity scores for normalization if needed
    all_topic_sims = []
    all_readme_sims = []
    repo_data = []
    
    # First pass to collect all scores
    for r in repos:
        if r["name"].lower() == repo_name.lower():
            continue
        
        # Get topic similarity
        t = get_topics(r["owner"]["login"], r["name"])
        common = set(t) & set(topics)
        topic_sim = 0
        if has_topics and t:
            topic_sim = len(common)/max(1, len(set(t) | set(topics)))
        all_topic_sims.append(topic_sim)
        
        # Get README similarity
        other_readme = ""
        readme_sim = 0
        if has_readme:
            other_readme = get_readme_content(r["owner"]["login"], r["name"])
            readme_sim = compute_readme_similarity(readme_content, other_readme)
        all_readme_sims.append(readme_sim)
        
        repo_data.append((r["full_name"], r.get("description", ""), list(common), topic_sim, readme_sim))
    
    # Normalize scores if we have data
    topic_max = max(all_topic_sims) if all_topic_sims else 1
    readme_max = max(all_readme_sims) if all_readme_sims else 1
    
    # Second pass to calculate combined scores
    for full_name, desc, common, topic_sim, readme_sim in repo_data:
        # Normalize if we have non-zero maximums
        norm_topic_sim = topic_sim / topic_max if topic_max > 0 else 0
        norm_readme_sim = readme_sim / readme_max if readme_max > 0 else 0
        
        # Combined score
        combined_score = (
            effective_weight_topics * norm_topic_sim + 
            (1 - effective_weight_topics) * norm_readme_sim
        )
        
        if combined_score > 0.1:  # Threshold for considering repositories as related
            related.append((full_name, desc, common, combined_score))
    
    return sorted(related, key=lambda x: -x[3])

def update_readme(related):
    """
    Update README.md with adjacent repositories.
    Completely replaces the existing Adjacent Repositories section.
    
    Args:
        related (list): List of tuples containing repository information
                        Each tuple is expected to be (full_name, desc, tags, _)
    """
    # Read existing README
    with open("README.md", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    header = "## 🔗 Adjacent Repositories"
    
    # Prepare the new block of repositories
    block = [f"{header}\n\n"]
    
    # Take the first 5 repositories
    for full_name, desc, tags, score in related[:5]:
        url = f"https://github.com/{full_name}"
        
        # Clean up description
        clean_desc = desc.strip() if desc else ""
        desc_str = f" — {clean_desc}" if clean_desc else ""
        
        block.append(f"- [{full_name}]({url}){desc_str}\n")
    
    # Find and replace the entire section
    new_lines = []
    section_started = False
    
    for line in lines:
        if line.startswith("## 🔗 Adjacent Repositories"):
            section_started = True
            new_lines.extend(block)
        elif section_started and line.startswith("## "):
            # Another section starts, stop replacing
            section_started = False
            new_lines.append(line)
        elif not section_started:
            new_lines.append(line)
    
    # If section was not found, append at the end
    if not any(header in line for line in new_lines):
        new_lines.extend(["\n"] + block)
    
    # Write back to README
    with open("README.md", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    owner, repo = REPO.split("/")
    topics = get_topics(owner, repo)
    method = os.getenv("SIMILARITY_METHOD", "topics").lower()
    
    print(f"Finding adjacent repositories using method: {method}")
    
    # Check if we have topics
    has_topics = len(topics) > 0
    if not has_topics:
        print("Warning: No topics found for this repository")
    
    # Get README content regardless of method for potential fallback
    readme_content = get_readme_content(owner, repo)
    has_readme = len(readme_content) > 0
    if not has_readme:
        print("Warning: No README content found or failed to parse")
    
    # Determine which method to use, with fallbacks if necessary
    if method == "topics":
        if has_topics:
            related = find_adjacent_by_topics(owner, repo, topics)
        else:
            print("Falling back to README similarity since no topics are available")
            if has_readme:
                related = find_adjacent_by_readme(owner, repo, readme_content)
            else:
                print("No viable similarity method available. Both topics and README are missing.")
                related = []
    elif method == "readme":
        if has_readme:
            related = find_adjacent_by_readme(owner, repo, readme_content)
        else:
            print("Falling back to topic similarity since README is not available")
            if has_topics:
                related = find_adjacent_by_topics(owner, repo, topics)
            else:
                print("No viable similarity method available. Both topics and README are missing.")
                related = []
    elif method == "combined":
        weight = float(os.getenv("TOPIC_WEIGHT", "0.5"))
        related = find_adjacent_combined(owner, repo, topics, readme_content, weight)
    else:
        print(f"Unrecognized method '{method}', using best available method")
        if has_topics and has_readme:
            print("Using combined similarity")
            weight = float(os.getenv("TOPIC_WEIGHT", "0.5"))
            related = find_adjacent_combined(owner, repo, topics, readme_content, weight)
        elif has_topics:
            print("Using topic similarity")
            related = find_adjacent_by_topics(owner, repo, topics)
        elif has_readme:
            print("Using README similarity")
            related = find_adjacent_by_readme(owner, repo, readme_content)
        else:
            print("No viable similarity method available. Both topics and README are missing.")
            related = []
    
    if related:
        update_readme(related)
        print("README updated with adjacent repositories.")
    else:
        print("No adjacent repos found.")
