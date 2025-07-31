#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDAS Pipeline Automated Job Scheduler
Automatically parses the all_shell.conf file and submits qsub jobs
Supports dependency management and error handling
"""

import os
import sys
import re
import time
import subprocess
import argparse
import glob
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional
import logging

class QsubScheduler:
    def __init__(self, shell_conf_file: str, output_dir: str, 
                 queue_name: str = "stereo.q", max_concurrent: int = 10,
                 retry_times: int = 3, wait_time: int = 30, dry_run: bool = False):
        """
        Initialize the scheduler
        
        Args:
            shell_conf_file: Path to all_shell.conf file
            output_dir: Output directory
            queue_name: Queue name
            max_concurrent: Maximum number of concurrent jobs
            retry_times: Number of retries
            wait_time: Wait time between jobs (seconds)
        """
        self.shell_conf_file = shell_conf_file
        self.output_dir = output_dir
        self.queue_name = queue_name
        self.max_concurrent = max_concurrent
        self.retry_times = retry_times
        self.wait_time = wait_time
        self.dry_run = dry_run
        
        # Create qsub dedicated subdirectory
        self.qsub_dir = os.path.join(output_dir, "qsub_info")
        os.makedirs(self.qsub_dir, exist_ok=True)
        os.makedirs(os.path.join(self.qsub_dir, "logs"), exist_ok=True)
        
        # Job status tracking
        self.job_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.job_status: Dict[str, str] = {}  # pending, running, completed, failed
        self.job_ids: Dict[str, str] = {}  # shell_file -> qsub_job_id
        self.running_jobs: Set[str] = set()
        self.completed_jobs: Set[str] = set()
        self.failed_jobs: Set[str] = set()
        
        # Log settings
        self.setup_logging()
        
    def setup_logging(self):
        """Set up logging"""
        log_file = os.path.join(self.qsub_dir, "qsub_scheduler.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def parse_shell_conf(self) -> List[Tuple[str, str]]:
        """
        Parse the all_shell.conf file
        
        Returns:
            List of (dependent_job, current_job) tuples
        """
        dependencies = []
        
        if not os.path.exists(self.shell_conf_file):
            raise FileNotFoundError(f"Shell conf file not found: {self.shell_conf_file}")
            
        with open(self.shell_conf_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        dependent_job = parts[0].strip()
                        current_job = parts[1].strip()
                        dependencies.append((dependent_job, current_job))
                        
        self.logger.info(f"Parsed {len(dependencies)} job dependencies from {self.shell_conf_file}")
        return dependencies
    
    def build_dependency_graph(self, dependencies: List[Tuple[str, str]]):
        """Build dependency graph"""
        # First initialize dependency sets for all jobs
        all_jobs = set()
        for dependent_job, current_job in dependencies:
            all_jobs.add(dependent_job)
            all_jobs.add(current_job)
            # Initialize job status
            self.job_status[dependent_job] = "pending"
            self.job_status[current_job] = "pending"
        
        # Ensure all jobs are in the dependency graph
        for job in all_jobs:
            if job not in self.job_dependencies:
                self.job_dependencies[job] = set()
        
        # Establish dependencies
        for dependent_job, current_job in dependencies:
            self.job_dependencies[current_job].add(dependent_job)
            
        self.logger.info(f"Built dependency graph with {len(self.job_status)} jobs")
        
    def get_job_info(self, shell_file: str) -> Tuple[int, int]:
        """
        Parse resource requirements from shell file path
        
        Args:
            shell_file: Path to shell file
            
        Returns:
            (cpu, memory) tuple
        """
        # Parse format: path:cpu:X:mem:YG
        match = re.search(r':cpu:(\d+):mem:(\d+)G', shell_file)
        if match:
            cpu = int(match.group(1))
            memory = int(match.group(2))
            return cpu, memory
        else:
            # Default resource allocation
            return 2, 20
            
    def create_qsub_script(self, shell_file: str, cpu: int, memory: int) -> str:
        """
        Create qsub script (using your successful command format)
        
        Args:
            shell_file: Path to shell file
            cpu: Number of CPUs
            memory: Memory size (GB)
        
        Returns:
            qsub script content
        """
        # Extract shell file path
        shell_path = shell_file.split(':')[0]
        
        # Create qsub script (using your successful command format)
        #qsub_script = f"""qsub -cwd -q {self.queue_name} -l num_proc={cpu},vf={memory}G {os.path.abspath(shell_path)}
        # Generate log file path
        shell_basename = os.path.basename(shell_path)
        log_prefix = os.path.splitext(shell_basename)[0]  # Remove .sh suffix
        log_dir = os.path.join(self.qsub_dir, "logs")
        
        qsub_script = f"""qsub -cwd -q {self.queue_name} -l num_proc={cpu},vf={memory}G -o {log_dir}/{log_prefix}.o -e {log_dir}/{log_prefix}.e {os.path.abspath(shell_path)}
"""
        return qsub_script
        
    def submit_job(self, shell_file: str) -> Optional[str]:
        """
        Submit a single job
        
        Args:
            shell_file: Path to shell file
        
        Returns:
            qsub job ID or None
        """
        try:
            cpu, memory = self.get_job_info(shell_file)
            
            # Create qsub script
            qsub_script = self.create_qsub_script(shell_file, cpu, memory)
            
            # Create temporary qsub script file
            shell_path = shell_file.split(':')[0]
            qsub_script_file = os.path.join(self.qsub_dir, f"{os.path.basename(shell_path)}.qsub")
            
            with open(qsub_script_file, 'w') as f:
                f.write(qsub_script)
            
            if self.dry_run:
                # dry-run mode: only show jobs to be submitted
                print(f"[DRY-RUN] Job to be submitted: {shell_path}")
                print(f"[DRY-RUN] Resources: CPU={cpu}, Memory={memory}G")
                print(f"[DRY-RUN] Queue: {self.queue_name}")
                print(f"[DRY-RUN] qsub script saved to: {qsub_script_file}")
                print("-" * 50)
                return "DRY_RUN_JOB_ID"
            else:
                # Execute qsub script directly
                result = subprocess.run(['bash', qsub_script_file], 
                                      capture_output=True, text=True, check=True)
                
                # Parse job ID
                job_id = result.stdout.strip()
                self.logger.info(f"Submitted job {job_id} for {shell_file}")
                
                # Clean up temporary file
 #               os.remove(qsub_script_file)
                
                return job_id
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to submit job for {shell_file}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error submitting job for {shell_file}: {e}")
            return None
            
    def check_job_status(self, job_id: str) -> str:
        """
        Check job status (adapted for special cluster environments)
        
        Args:
            job_id: qsub job ID
        
        Returns:
            Job status: running, completed, failed
        """
        try:
            # Use qstat to check job status (do not specify job_id, get all jobs)
            result = subprocess.run(['qstat'], 
                                  capture_output=True, text=True)
            
            # Parse qstat output, find specific job_id
            output = result.stdout
            # Find specific job_id in output
            for line in output.split('\n'):
                if job_id in line:
                    # Found job, parse status
                    parts = line.split()
                    if len(parts) >= 5:
                        state = parts[4]  # Status in column 5
                        # Make a judgment based on status
                        if state == 'r':
                            return "running"  # Running
                        elif state == 'qw':
                            return "running"  # Waiting
                        elif state == 'Eqw':
                            return "failed"   # Error queue waiting
                        elif state == 'hqw':
                            return "running"  # Suspended waiting
                        elif state == 'dr':
                            return "running"  # Deleted but still running
                        elif state == 'dqw':
                            return "failed"   # Deleted and waiting
                        elif state == 'e':
                            return "failed"   # Error state
                        else:
                            return "running"  # Other states considered running
            
            # If job_id not found in qstat output, job may be completed or failed
            self.logger.info(f"Job {job_id} not found in qstat output, checking completion...")
            return self.check_job_completion_by_output(job_id)
                    
        except Exception as e:
            self.logger.error(f"Error checking job status for {job_id}: {e}")
            return "failed"
    
    def check_job_completion_by_output(self, job_id: str) -> str:
        """
        Determine job completion by checking output files
        
        Args:
            job_id: qsub job ID
        
        Returns:
            Job status: completed, failed
        """
        try:
            # Find the corresponding shell file based on job_id, then find the corresponding log file
            shell_file = None
            for job, jid in self.job_ids.items():
                if jid == job_id:
                    shell_file = job
                    break
            
            if not shell_file:
                self.logger.warning(f"Could not find shell file for job {job_id}")
                return "failed"
            
            # Generate log file path based on shell file
            shell_path = shell_file.split(':')[0]
            shell_basename = os.path.basename(shell_path)
            log_prefix = os.path.splitext(shell_basename)[0]  # Remove .sh suffix
            logs_dir = os.path.join(self.qsub_dir, "logs")
            
            output_file = os.path.join(logs_dir, f"{log_prefix}.o")
            error_file = os.path.join(logs_dir, f"{log_prefix}.e")
            
            self.logger.info(f"Checking completion for job {job_id}, shell: {shell_file}")
            self.logger.info(f"Looking for log files: {output_file}, {error_file}")
            
            # Check if error file has content
            if os.path.exists(error_file) and os.path.getsize(error_file) > 0:
                with open(error_file, 'r') as f:
                    error_content = f.read()
                    if "error" in error_content.lower() or "failed" in error_content.lower():
                        self.logger.warning(f"Job {job_id} failed based on error file: {error_file}")
                        return "failed"
            
            # Check if output file contains success information
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    output_content = f.read()
                    
                # Parse SDAS exit code
                sdas_exit_code = None
                sdas_status = None
                sdas_error = None
                
                for line in output_content.split('\n'):
                    if line.startswith('SDAS_EXIT_CODE:'):
                        try:
                            sdas_exit_code = int(line.split(':')[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif line.startswith('SDAS_STATUS:'):
                        sdas_status = line.split(':')[1].strip()
                    elif line.startswith('SDAS_ERROR:'):
                        sdas_error = line.split(':', 1)[1].strip()
                
                self.logger.info(f"Job {job_id} output analysis:")
                self.logger.info(f"  - SDAS Exit Code: {sdas_exit_code}")
                self.logger.info(f"  - SDAS Status: {sdas_status}")
                self.logger.info(f"  - SDAS Error: {sdas_error}")
                
                # Mainly rely on SDAS exit code to make a judgment
                if sdas_exit_code is not None:
                    if sdas_exit_code == 0:
                        self.logger.info(f"Job {job_id} completed successfully (SDAS exit code: 0)")
                        return "completed"
                    else:
                        error_msg = f"Job {job_id} failed (SDAS exit code: {sdas_exit_code})"
                        if sdas_error:
                            error_msg += f" - {sdas_error}"
                        self.logger.error(error_msg)
                        return "failed"
                
                # If no SDAS exit code, use a simple fallback judgment
                if "all commands done" in output_content:
                    self.logger.info(f"Job {job_id} completed (success flag found): {output_file}")
                    return "completed"
                else:
                    # Check file size, if file is small or empty, job might still be running
                    file_size = os.path.getsize(output_file)
                    if file_size < 500:  # Increase threshold to 500 bytes, give more time for job to start
                        self.logger.warning(f"Job {job_id} output file is small ({file_size} bytes), job might still be running")
                        return "running"
                    else:
                        # If file is large but no success flag, check for error information
                        if "error" in output_content.lower() or "failed" in output_content.lower():
                            self.logger.error(f"Job {job_id} failed (error indicators found in output)")
                            return "failed"
                        else:
                            self.logger.warning(f"Job {job_id} has substantial output ({file_size} bytes) but no clear success/error indicators, assuming still running")
                            return "running"
            
            # If no clear success/failure information found, but job is not in queue, need more careful judgment
            self.logger.warning(f"Job {job_id} not in queue and no clear completion indicators found")
            # Check if output file exists, if it does but content is small, job might still be running
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                if file_size < 100:
                    self.logger.warning(f"Job {job_id} output file is small ({file_size} bytes), assuming still running")
                    return "running"
                else:
                    self.logger.info(f"Job {job_id} not in queue but has substantial output, assuming completed")
                    return "completed"
            else:
                self.logger.warning(f"Job {job_id} not in queue and no output file found, assuming failed")
                return "failed"
            
        except Exception as e:
            self.logger.error(f"Error checking job completion for {job_id}: {e}")
            return "failed"
            
    def get_ready_jobs(self) -> List[str]:
        """
        Get jobs that can be submitted (dependencies completed)
        
        Returns:
            List of jobs ready to submit
        """
        ready_jobs = []
        for job, dependencies in self.job_dependencies.items():
            if self.job_status[job] == "pending":
                if not dependencies or all(self.job_status[dep] == "completed" for dep in dependencies):
                    ready_jobs.append(job)
        return ready_jobs
        
    def update_job_status(self):
        """Update the status of all running jobs"""
        for job, job_id in self.job_ids.items():
            if self.job_status[job] == "running":
                status = self.check_job_status(job_id)
                if status != "running":
                    self.job_status[job] = status
                    if status == "completed":
                        self.completed_jobs.add(job)
                        self.running_jobs.discard(job)
                        self.logger.info(f"Job completed: {job}")
                    elif status == "failed":
                        self.failed_jobs.add(job)
                        self.running_jobs.discard(job)
                        self.logger.error(f"Job failed: {job}")
                        
    def run(self):
        """Run the scheduler"""
        if self.dry_run:
            self.logger.info("Starting SDAS Pipeline Qsub Scheduler (DRY-RUN MODE)")
            print("=" * 60)
            print("DRY-RUN MODE: No jobs will actually be submitted to the queue")
            print("=" * 60)
        else:
            self.logger.info("Starting SDAS Pipeline Qsub Scheduler")
        # Parse dependencies
        dependencies = self.parse_shell_conf()
        self.build_dependency_graph(dependencies)
        # Only for logging - calculate truly independent jobs (not depended on by others)
        all_jobs = set(self.job_status.keys())
        jobs_that_are_depended_on = set()
        for deps in self.job_dependencies.values():
            jobs_that_are_depended_on.update(deps)
        independent_jobs = all_jobs - jobs_that_are_depended_on
        self.logger.info(f"Found {len(independent_jobs)} independent jobs (jobs that are not depended on by others)")
        if self.dry_run:
            # dry-run mode: show all job info (only output job_dependencies content)
            print(f"\nParsed {len(self.job_status)} jobs:")
            print("-" * 60)
            for job in sorted(self.job_status.keys()):
                cpu, memory = self.get_job_info(job)
                dependencies = list(self.job_dependencies.get(job, set()))
                print(f"Job: {job}")
                print(f"  Resources: CPU={cpu}, Memory={memory}G")
                print(f"  Dependencies: {dependencies if dependencies else 'None'}")
                print()
            print("=" * 60)
            print("DRY-RUN COMPLETE")
            
            # Also generate job list file in dry-run mode
            submitted_jobs_file = os.path.join(self.output_dir, "submitted_jobs.txt")
            with open(submitted_jobs_file, 'w') as f:
                f.write("SDAS Pipeline Submitted Jobs List (DRY-RUN MODE)\n")
                f.write("=" * 50 + "\n\n")
                f.write("Note: This is dry-run mode, no jobs were actually submitted to the queue\n\n")
                f.write(f"Total Jobs to Submit: {len(self.job_status)}\n\n")
                
                for job in sorted(self.job_status.keys()):
                    cpu, memory = self.get_job_info(job)
                    dependencies = list(self.job_dependencies.get(job, set()))
                    f.write(f"Job: {job}\n")
                    f.write(f"  Shell Script: {job.split(':')[0]}\n")
                    f.write(f"  Resources: CPU={cpu}, Memory={memory}G\n")
                    f.write(f"  Dependencies: {dependencies if dependencies else 'None'}\n")
                    f.write("-" * 40 + "\n")
            
            self.logger.info(f"Dry-run jobs list saved to {submitted_jobs_file}")
            
            # Generate all qsub scripts for viewing in dry-run mode
            print("\nGenerating qsub scripts for viewing...")
            for job in sorted(self.job_status.keys()):
                cpu, memory = self.get_job_info(job)
                qsub_script = self.create_qsub_script(job, cpu, memory)
                
                # Create qsub script file
                shell_path = job.split(':')[0]
                qsub_script_file = os.path.join(self.qsub_dir, f"{os.path.basename(shell_path)}.qsub")
                
                with open(qsub_script_file, 'w') as f:
                    f.write(qsub_script)
                
                print(f"  Generated: {qsub_script_file}")
            
            print(f"\nAll qsub scripts have been saved to: {self.qsub_dir}")
            return
        # Main scheduling loop (keep original logic)
        while len(self.completed_jobs) + len(self.failed_jobs) < len(self.job_status):
            self.update_job_status()
            ready_jobs = self.get_ready_jobs()
            available_slots = self.max_concurrent - len(self.running_jobs)
            for job in ready_jobs[:available_slots]:
                job_id = self.submit_job(job)
                if job_id:
                    self.job_ids[job] = job_id
                    self.job_status[job] = "running"
                    self.running_jobs.add(job)
                    self.logger.info(f"Started job {job_id} for {job}")
                else:
                    self.job_status[job] = "failed"
                    self.failed_jobs.add(job)
                    self.logger.error(f"Failed to submit job for {job}")
            if ready_jobs or self.running_jobs:
                time.sleep(self.wait_time)
            else:
                if len(self.failed_jobs) > 0:
                    self.logger.error("Some jobs failed, stopping scheduler")
                    break
        self.generate_report()
        
    def generate_report(self):
        """Generate execution report"""
        report_file = os.path.join(self.qsub_dir, "qsub_execution_report.txt")
        
        with open(report_file, 'w') as f:
            f.write("SDAS Pipeline Qsub Execution Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Jobs: {len(self.job_status)}\n")
            f.write(f"Completed Jobs: {len(self.completed_jobs)}\n")
            f.write(f"Failed Jobs: {len(self.failed_jobs)}\n")
            f.write(f"Running Jobs: {len(self.running_jobs)}\n\n")
            
            f.write("Completed Jobs:\n")
            for job in sorted(self.completed_jobs):
                f.write(f"  ✓ {job}\n")
                
            f.write("\nFailed Jobs:\n")
            for job in sorted(self.failed_jobs):
                f.write(f"  ✗ {job}\n")
                
            f.write("\nRunning Jobs:\n")
            for job in sorted(self.running_jobs):
                f.write(f"  ⟳ {job}\n")
                
        self.logger.info(f"Execution report saved to {report_file}")
        
        # Generate submitted job ID list
        submitted_jobs_file = os.path.join(self.output_dir, "submitted_jobs.txt")
        with open(submitted_jobs_file, 'w') as f:
            f.write("SDAS Pipeline Submitted Jobs List\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Total Submitted Jobs: {len(self.job_ids)}\n\n")
            
            for job, job_id in self.job_ids.items():
                status = self.job_status.get(job, "unknown")
                f.write(f"Job: {job}\n")
                f.write(f"  ID: {job_id}\n")
                f.write(f"  Status: {status}\n")
                f.write(f"  Shell Script: {job.split(':')[0]}\n")
                f.write("-" * 40 + "\n")
        
        self.logger.info(f"Submitted jobs list saved to {submitted_jobs_file}")
        
        # Print summary
        print(f"\n{'='*50}")
        print("SDAS Pipeline Qsub Execution Summary")
        print(f"{'='*50}")
        print(f"Total Jobs: {len(self.job_status)}")
        print(f"Submitted: {len(self.job_ids)}")
        print(f"Completed: {len(self.completed_jobs)}")
        print(f"Failed: {len(self.failed_jobs)}")
        print(f"Running: {len(self.running_jobs)}")
        print(f"{'='*50}")

def main():
    parser = argparse.ArgumentParser(
        description="SDAS Pipeline Automated Job Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python auto_qsub_scheduler.py -c all_shell.conf -o ./output
  python auto_qsub_scheduler.py -c all_shell.conf -o ./output -q stereo.q -m 20
  python auto_qsub_scheduler.py -c all_shell.conf -o ./output --dry-run
        """
    )
    
    parser.add_argument("-c", "--conf", required=True,
                       help="Path to all_shell.conf file")
    parser.add_argument("-o", "--output", required=True,
                       help="Output directory")
    parser.add_argument("-q", "--queue", default="stereo.q",
                       help="Queue name (default: stereo.q)")
    parser.add_argument("-m", "--max-concurrent", type=int, default=10,
                       help="Maximum number of concurrent jobs (default: 10)")
    parser.add_argument("-r", "--retry", type=int, default=3,
                       help="Number of retries (default: 3)")
    parser.add_argument("-w", "--wait", type=int, default=30,
                       help="Wait time between jobs (seconds) (default: 30)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview mode, do not actually submit jobs")
    
    args = parser.parse_args()
    
    # Check input file
    if not os.path.exists(args.conf):
        print(f"Error: Config file does not exist: {args.conf}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Create and run scheduler
    scheduler = QsubScheduler(
        shell_conf_file=args.conf,
        output_dir=args.output,
        queue_name=args.queue,
        max_concurrent=args.max_concurrent,
        retry_times=args.retry,
        wait_time=args.wait,
        dry_run=args.dry_run
    )
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print("\nExecution interrupted by user")
        scheduler.generate_report()
    except Exception as e:
        print(f"Execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 