#!/usr/bin/env python3
"""
Generate test data to verify pagination functionality.
Creates 25 notes to test pagination with default limit of 10.
"""
import subprocess
import sys
import time

def generate_test_notes(count=25):
    """Generate test notes to verify pagination."""
    
    print(f"=" * 60)
    print(f" Generating {count} test notes for pagination testing")
    print(f"=" * 60)
    print()
    
    topics = [
        ("Python Tips", "python", "Tips and tricks for Python programming"),
        ("JavaScript Notes", "javascript", "Modern JavaScript features and patterns"),
        ("Machine Learning", "ml, ai", "Introduction to machine learning concepts"),
        ("Docker Commands", "docker, devops", "Essential Docker commands for development"),
        ("Git Workflow", "git, workflow", "Best practices for Git branching strategies"),
        ("React Hooks", "react, frontend", "Understanding React hooks and their usage"),
        ("Database Design", "database, sql", "Relational database design principles"),
        ("API Design", "api, rest", "RESTful API design best practices"),
        ("Testing Strategies", "testing, qa", "Unit testing and integration testing approaches"),
        ("CI/CD Pipeline", "cicd, devops", "Setting up continuous integration and deployment"),
        ("Cloud Architecture", "cloud, aws", "Microservices architecture on cloud platforms"),
        ("Security Basics", "security", "Web application security fundamentals"),
        ("Performance Optimization", "performance", "Techniques for optimizing application performance"),
        ("Code Review", "code-review", "Effective code review practices"),
        ("Documentation", "documentation", "Writing clear and comprehensive documentation"),
        ("Agile Methods", "agile, scrum", "Agile development methodologies overview"),
        ("Data Structures", "algorithms", "Common data structures and their use cases"),
        ("Design Patterns", "patterns, oop", "Gang of Four design patterns explained"),
        ("Linux Commands", "linux, terminal", "Essential Linux command line utilities"),
        ("CSS Layouts", "css, frontend", "Flexbox and Grid layout techniques"),
        ("TypeScript Guide", "typescript", "TypeScript type system and features"),
        ("Node.js Basics", "nodejs, backend", "Getting started with Node.js development"),
        ("GraphQL API", "graphql, api", "Building APIs with GraphQL"),
        ("Kubernetes 101", "kubernetes, k8s", "Container orchestration with Kubernetes"),
        ("Redis Caching", "redis, cache", "Using Redis for application caching"),
        ("MongoDB Guide", "mongodb, nosql", "Document database design with MongoDB"),
        ("WebSockets", "websockets, realtime", "Real-time communication with WebSockets"),
        ("OAuth 2.0", "oauth, auth", "Understanding OAuth 2.0 authentication flow"),
        ("Web Accessibility", "a11y, frontend", "Making web applications accessible"),
        ("PWA Development", "pwa, mobile", "Progressive Web App development guide"),
    ]
    
    success_count = 0
    failed_count = 0
    
    for i in range(1, count + 1):
        topic_idx = (i - 1) % len(topics)
        title_base, tags, summary = topics[topic_idx]
        
        # Create unique title
        title = f"{title_base} #{i}"
        
        # Create content
        content = f"This is test note #{i} about {title_base.lower()}. {summary}. Created for pagination testing."
        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",")]
        
        # Build command
        cmd = [
            "localbrain", "collect", "note", "add", content,
            "--title", title
        ]
        
        # Add tags
        for tag in tag_list:
            cmd.extend(["--tags", tag])
        
        print(f"[{i}/{count}] Creating: {title}")
        print(f"  Tags: {', '.join(tag_list)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                success_count += 1
                print(f"  ✓ Success")
            else:
                failed_count += 1
                print(f"  ✗ Failed: {result.stderr.strip()}")
        
        except subprocess.TimeoutExpired:
            failed_count += 1
            print(f"  ✗ Timeout")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Error: {str(e)}")
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.1)
        
        print()
    
    # Summary
    print(f"=" * 60)
    print(f" Generation Complete!")
    print(f"=" * 60)
    print(f"  Total: {count}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print()
    
    if success_count > 0:
        print(f"Next steps:")
        print(f"  1. Open web UI: http://127.0.0.1:11201")
        print(f"  2. Navigate to 'Knowledge Collected' > 'Notes'")
        print(f"  3. Verify pagination shows 10 items per page")
        print(f"  4. Click 'Next →' to see page 2 and 3")
        print(f"  5. Verify showing text: 'Showing 1-10', 'Showing 11-20', etc.")
        print()

if __name__ == "__main__":
    count = 25
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [count]")
            sys.exit(1)
    
    generate_test_notes(count)
