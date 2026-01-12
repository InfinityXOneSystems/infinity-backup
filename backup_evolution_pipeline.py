#!/usr/bin/env python3
"""
Autonomous Backup and Evolution Pipeline
Integrates Manus + Vertex AI + Vision Cortex for comprehensive repository management
"""

import os
import sys
import json
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Any
import time

# Google Cloud imports
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "google-genai"], check=True)
    from google import genai
    from google.genai import types


class AutoEvolutionPipeline:
    """Autonomous backup and evolution pipeline with AI integration"""
    
    def __init__(self):
        self.base_dir = Path("/home/ubuntu/auto-evolution-pipeline")
        self.backup_dir = self.base_dir / "infinity-backup"
        self.repos_dir = self.base_dir / "repositories"
        self.reports_dir = self.base_dir / "reports"
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize Vertex AI client
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        self.client = genai.Client(api_key=self.gemini_api_key)
        
        # Initialize GCP Service Account
        self.gcp_sa_key = os.environ.get("GCP_SA_KEY")
        
        # Create directories
        self.repos_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # Load repository inventory
        self.repos = self.load_repository_inventory()
        
        # Evolution metrics
        self.metrics = {
            "total_repos": len(self.repos),
            "backed_up": 0,
            "analyzed": 0,
            "evolved": 0,
            "errors": [],
            "recommendations": [],
            "friction_points": [],
            "future_timelines": []
        }
    
    def load_repository_inventory(self) -> List[Dict[str, Any]]:
        """Load repository inventory from JSON"""
        inventory_path = Path("/home/ubuntu/repo_inventory.json")
        with open(inventory_path, 'r') as f:
            return json.load(f)
    
    def run_command(self, cmd: str, cwd: Path = None) -> tuple:
        """Execute shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd or self.base_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def backup_repository(self, repo: Dict[str, Any]) -> bool:
        """Clone and backup a single repository"""
        repo_name = repo['name']
        repo_url = repo['url']
        
        print(f"[BACKUP] Processing {repo_name}...")
        
        repo_path = self.repos_dir / repo_name
        
        # Clone repository
        if repo_path.exists():
            # Update existing repo
            returncode, stdout, stderr = self.run_command(
                f"git pull origin main || git pull origin master",
                cwd=repo_path
            )
        else:
            # Clone new repo
            returncode, stdout, stderr = self.run_command(
                f"gh repo clone {repo_url} {repo_path}"
            )
        
        if returncode == 0:
            self.metrics["backed_up"] += 1
            print(f"[SUCCESS] Backed up {repo_name}")
            return True
        else:
            error_msg = f"Failed to backup {repo_name}: {stderr}"
            self.metrics["errors"].append(error_msg)
            print(f"[ERROR] {error_msg}")
            return False
    
    def analyze_repository_with_ai(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository using Vertex AI (Gemini)"""
        repo_name = repo['name']
        repo_path = self.repos_dir / repo_name
        
        print(f"[ANALYZE] Analyzing {repo_name} with Vertex AI...")
        
        if not repo_path.exists():
            return {"error": "Repository not found"}
        
        # Gather repository metadata
        metadata = self.gather_repo_metadata(repo_path)
        
        # Create analysis prompt
        prompt = f"""
You are an advanced AI system analyzer for the Infinity X One Systems ecosystem.

Analyze this repository and provide comprehensive insights:

Repository: {repo_name}
Description: {repo.get('description', 'N/A')}
Last Updated: {repo.get('updatedAt', 'N/A')}

Metadata:
{json.dumps(metadata, indent=2)}

Provide analysis in the following structure:
1. **Purpose & Function**: What this repository does
2. **Code Quality**: Assessment of code structure, patterns, and maintainability
3. **Integration Points**: How it connects with other system components
4. **Optimization Opportunities**: Specific improvements for performance, architecture, or functionality
5. **Evolution Recommendations**: Next-generation enhancements aligned with 110% protocol
6. **Friction Points**: Current bottlenecks, technical debt, or limitations
7. **Future Timeline Scenarios**: 3 possible evolution paths (conservative, moderate, aggressive)
8. **Vision Cortex Integration**: How this can leverage infinity-matrix capabilities
9. **AutoML Potential**: Machine learning enhancement opportunities
10. **System Ecosystem Role**: Position in the overall 1000 system map

Be specific, actionable, and forward-thinking.
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
            
            analysis = {
                "repo_name": repo_name,
                "timestamp": self.timestamp,
                "analysis": response.text,
                "metadata": metadata
            }
            
            self.metrics["analyzed"] += 1
            print(f"[SUCCESS] Analyzed {repo_name}")
            return analysis
            
        except Exception as e:
            error_msg = f"AI analysis failed for {repo_name}: {str(e)}"
            self.metrics["errors"].append(error_msg)
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}
    
    def gather_repo_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """Gather repository metadata for analysis"""
        metadata = {
            "files": [],
            "languages": {},
            "size_kb": 0,
            "commit_count": 0,
            "branches": []
        }
        
        try:
            # Count files and get structure
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(repo_path)
                    metadata["files"].append(str(rel_path))
                    
                    # Track languages by extension
                    ext = file_path.suffix
                    if ext:
                        metadata["languages"][ext] = metadata["languages"].get(ext, 0) + 1
            
            # Get repository size
            returncode, stdout, stderr = self.run_command(
                f"du -sk {repo_path}",
                cwd=repo_path.parent
            )
            if returncode == 0:
                metadata["size_kb"] = int(stdout.split()[0])
            
            # Get commit count
            returncode, stdout, stderr = self.run_command(
                "git rev-list --count HEAD",
                cwd=repo_path
            )
            if returncode == 0:
                metadata["commit_count"] = int(stdout.strip())
            
            # Get branches
            returncode, stdout, stderr = self.run_command(
                "git branch -r",
                cwd=repo_path
            )
            if returncode == 0:
                metadata["branches"] = [b.strip() for b in stdout.split('\n') if b.strip()]
        
        except Exception as e:
            metadata["error"] = str(e)
        
        return metadata
    
    def generate_system_evolution_analysis(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive system-wide evolution analysis"""
        print("[EVOLUTION] Generating system-wide evolution analysis...")
        
        # Compile all analyses
        compiled_analyses = "\n\n".join([
            f"### {a['repo_name']}\n{a.get('analysis', 'No analysis available')}"
            for a in analyses if 'analysis' in a
        ])
        
        prompt = f"""
You are the Vision Cortex AI - the supreme system architect for Infinity X One Systems.

You have analyzed {len(analyses)} repositories. Now provide a comprehensive SYSTEM-WIDE evolution strategy.

Individual Repository Analyses:
{compiled_analyses[:50000]}  # Limit to avoid token overflow

Generate an exhaustive system evolution report with:

## 1. SYSTEM ARCHITECTURE OVERVIEW
- Current state of the entire ecosystem
- Interconnections and dependencies
- Modular system map (1000 system map concept)

## 2. OPTIMIZATION MATRIX
- Cross-repository optimization opportunities
- Consolidation recommendations
- Redundancy elimination strategies

## 3. 110% PROTOCOL IMPLEMENTATION
- Current capability assessment
- Gap analysis for reaching 110% operational capacity
- Specific enhancement roadmap

## 4. FRICTION POINTS & BOTTLENECKS
- System-wide friction points
- Performance bottlenecks
- Technical debt priorities
- Security vulnerabilities

## 5. THREE FUTURE TIMELINES
### Timeline A (Conservative - 6 months)
- Incremental improvements
- Risk mitigation focus
- Stability enhancements

### Timeline B (Moderate - 12 months)
- Balanced innovation and stability
- Strategic integrations
- Capability expansion

### Timeline C (Aggressive - 24 months)
- Revolutionary transformation
- Full Vision Cortex integration
- Quantum and universal enhancements
- ASI-human partnership framework

## 6. VERTEX AI & VISION CORTEX INTEGRATION
- AutoML implementation opportunities
- Gemini integration points
- Firestore optimization
- Real-time intelligence enhancement

## 7. AUTOMATION & WORKFLOW EVOLUTION
- Personal workflow automation
- Business process optimization
- AI-human collaboration enhancement
- Zero-intervention autonomous systems

## 8. RECOMMENDATIONS PRIORITY MATRIX
Rank all recommendations by:
- Impact (1-10)
- Effort (1-10)
- Priority (Critical/High/Medium/Low)
- Timeline (Immediate/Short/Medium/Long-term)

## 9. IMPLEMENTATION ROADMAP
- Phase 1: Foundation (Month 1-3)
- Phase 2: Enhancement (Month 4-6)
- Phase 3: Evolution (Month 7-12)
- Phase 4: Transcendence (Month 13-24)

## 10. SUCCESS METRICS & VALIDATION
- KPIs for each phase
- Validation checkpoints
- Triple-validation framework
- Continuous monitoring strategy

Be extremely detailed, specific, and actionable. This is the master blueprint for system evolution.
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
            
            evolution_analysis = {
                "timestamp": self.timestamp,
                "total_repos_analyzed": len(analyses),
                "system_evolution_strategy": response.text
            }
            
            print("[SUCCESS] Generated system evolution analysis")
            return evolution_analysis
            
        except Exception as e:
            error_msg = f"System evolution analysis failed: {str(e)}"
            self.metrics["errors"].append(error_msg)
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}
    
    def create_backup_archive(self) -> bool:
        """Create comprehensive backup archive"""
        print("[BACKUP] Creating backup archive...")
        
        backup_timestamp_dir = self.backup_dir / f"backup_{self.timestamp}"
        backup_timestamp_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all repositories to backup
        returncode, stdout, stderr = self.run_command(
            f"cp -r {self.repos_dir}/* {backup_timestamp_dir}/"
        )
        
        if returncode != 0:
            self.metrics["errors"].append(f"Backup archive creation failed: {stderr}")
            return False
        
        # Create backup manifest
        manifest = {
            "timestamp": self.timestamp,
            "total_repos": self.metrics["total_repos"],
            "backed_up": self.metrics["backed_up"],
            "repositories": [repo['name'] for repo in self.repos]
        }
        
        manifest_path = backup_timestamp_dir / "backup_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"[SUCCESS] Backup archive created at {backup_timestamp_dir}")
        return True
    
    def generate_exhaustive_report(self, analyses: List[Dict[str, Any]], 
                                   evolution_analysis: Dict[str, Any]) -> str:
        """Generate comprehensive markdown report"""
        print("[REPORT] Generating exhaustive report...")
        
        report = f"""# Autonomous Backup & Evolution Pipeline Report
**Generated**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Pipeline Version**: 1.0.0
**Integration**: Manus + Vertex AI + Vision Cortex

---

## Executive Summary

This report documents the comprehensive backup and evolution analysis of the Infinity X One Systems ecosystem, encompassing **{self.metrics['total_repos']} repositories**.

### Key Metrics
- **Total Repositories**: {self.metrics['total_repos']}
- **Successfully Backed Up**: {self.metrics['backed_up']}
- **AI Analyzed**: {self.metrics['analyzed']}
- **Evolution Recommendations**: Generated
- **Errors Encountered**: {len(self.metrics['errors'])}

---

## System-Wide Evolution Analysis

{evolution_analysis.get('system_evolution_strategy', 'Analysis not available')}

---

## Individual Repository Analyses

"""
        
        for analysis in analyses:
            if 'analysis' in analysis:
                report += f"""
### {analysis['repo_name']}

**Timestamp**: {analysis['timestamp']}

{analysis['analysis']}

**Metadata Summary**:
- Files: {len(analysis.get('metadata', {}).get('files', []))}
- Languages: {', '.join(analysis.get('metadata', {}).get('languages', {}).keys())}
- Size: {analysis.get('metadata', {}).get('size_kb', 0)} KB
- Commits: {analysis.get('metadata', {}).get('commit_count', 0)}

---

"""
        
        # Add errors section
        if self.metrics['errors']:
            report += "\n## Errors & Issues\n\n"
            for i, error in enumerate(self.metrics['errors'], 1):
                report += f"{i}. {error}\n"
        
        # Add footer
        report += f"""
---

## Pipeline Execution Details

- **Execution Time**: {self.timestamp}
- **Backup Location**: `/home/ubuntu/auto-evolution-pipeline/infinity-backup/backup_{self.timestamp}`
- **Report Location**: `/home/ubuntu/auto-evolution-pipeline/reports/evolution_report_{self.timestamp}.md`
- **Next Scheduled Run**: Daily at 12:00 AM UTC

---

**Generated by Autonomous Evolution Pipeline**
*Powered by Manus + Vertex AI + Vision Cortex*
"""
        
        # Save report
        report_path = self.reports_dir / f"evolution_report_{self.timestamp}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"[SUCCESS] Report generated at {report_path}")
        return str(report_path)
    
    def push_to_github(self) -> bool:
        """Push backup and reports to GitHub"""
        print("[GITHUB] Pushing to infinity-backup repository...")
        
        try:
            # Configure git
            self.run_command(
                'git config user.email "pipeline@infinityxone.systems"',
                cwd=self.backup_dir
            )
            self.run_command(
                'git config user.name "Auto Evolution Pipeline"',
                cwd=self.backup_dir
            )
            
            # Add all files
            self.run_command("git add -A", cwd=self.backup_dir)
            
            # Commit
            commit_msg = f"Automated backup and evolution analysis - {self.timestamp}"
            self.run_command(f'git commit -m "{commit_msg}"', cwd=self.backup_dir)
            
            # Push
            returncode, stdout, stderr = self.run_command(
                "git push origin main || git push origin master",
                cwd=self.backup_dir
            )
            
            if returncode == 0:
                print("[SUCCESS] Pushed to GitHub")
                return True
            else:
                self.metrics["errors"].append(f"GitHub push failed: {stderr}")
                print(f"[ERROR] GitHub push failed: {stderr}")
                return False
                
        except Exception as e:
            error_msg = f"GitHub push exception: {str(e)}"
            self.metrics["errors"].append(error_msg)
            print(f"[ERROR] {error_msg}")
            return False
    
    def execute_pipeline(self, sample_size: int = None):
        """Execute the complete backup and evolution pipeline"""
        print("="*80)
        print("AUTONOMOUS BACKUP & EVOLUTION PIPELINE")
        print("Manus + Vertex AI + Vision Cortex Integration")
        print("="*80)
        print()
        
        start_time = time.time()
        
        # Phase 1: Backup all repositories
        print(f"\n[PHASE 1] Backing up {self.metrics['total_repos']} repositories...")
        repos_to_process = self.repos[:sample_size] if sample_size else self.repos
        
        for i, repo in enumerate(repos_to_process, 1):
            print(f"[{i}/{len(repos_to_process)}] ", end="")
            self.backup_repository(repo)
        
        # Phase 2: AI Analysis
        print(f"\n[PHASE 2] Analyzing repositories with Vertex AI...")
        analyses = []
        
        # Analyze a representative sample for detailed analysis
        sample_repos = repos_to_process[:20] if len(repos_to_process) > 20 else repos_to_process
        
        for i, repo in enumerate(sample_repos, 1):
            print(f"[{i}/{len(sample_repos)}] ", end="")
            analysis = self.analyze_repository_with_ai(repo)
            if analysis and 'error' not in analysis:
                analyses.append(analysis)
        
        # Phase 3: System Evolution Analysis
        print(f"\n[PHASE 3] Generating system-wide evolution analysis...")
        evolution_analysis = self.generate_system_evolution_analysis(analyses)
        
        # Phase 4: Create Backup Archive
        print(f"\n[PHASE 4] Creating backup archive...")
        self.create_backup_archive()
        
        # Phase 5: Generate Report
        print(f"\n[PHASE 5] Generating exhaustive report...")
        report_path = self.generate_exhaustive_report(analyses, evolution_analysis)
        
        # Phase 6: Push to GitHub
        print(f"\n[PHASE 6] Pushing to GitHub...")
        self.push_to_github()
        
        # Summary
        elapsed_time = time.time() - start_time
        print("\n" + "="*80)
        print("PIPELINE EXECUTION COMPLETE")
        print("="*80)
        print(f"Total Time: {elapsed_time:.2f} seconds")
        print(f"Repositories Backed Up: {self.metrics['backed_up']}/{self.metrics['total_repos']}")
        print(f"Repositories Analyzed: {self.metrics['analyzed']}")
        print(f"Errors: {len(self.metrics['errors'])}")
        print(f"Report: {report_path}")
        print("="*80)
        
        return report_path


if __name__ == "__main__":
    # Check for sample mode
    sample_size = None
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"Running in SAMPLE MODE: Processing {sample_size} repositories")
    
    pipeline = AutoEvolutionPipeline()
    report_path = pipeline.execute_pipeline(sample_size=sample_size)
    
    print(f"\nReport available at: {report_path}")
