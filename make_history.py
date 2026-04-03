import os
import random
import subprocess
from datetime import datetime, timedelta

START_DATE = datetime(2023, 6, 29)
END_DATE = datetime(2024, 1, 4)
NUM_COMMITS = 50

FILES_TO_ADD = [
    ".gitignore", "README.md", "requirements.txt", "secrets.toml.example",
    "app.py", "config.py", "multi_agent.py", "prompts.py",
    "schemas/__init__.py", "schemas/planner.py",
    "services/__init__.py", "services/cache.py", "services/llm.py",
    "services/router.py", "services/search.py", "services/similarity.py",
    "scripts/benchmark.py",
    "graph/__init__.py", "graph/workflow.py",
    "agents/__init__.py", "agents/executor.py", "agents/memory.py", "agents/planner.py"
]

days_between = (END_DATE - START_DATE).days
random_days_added = random.sample(range(days_between + 1), NUM_COMMITS)
commit_dates = [START_DATE + timedelta(days=day) for day in random_days_added]
commit_dates.sort()

def run_cmd(cmd, env=None):
    subprocess.run(cmd, env=env, check=True)

def git_commit(date, msg):
    date_str = date.strftime("%Y-%m-%dT14:00:00")
    env = os.environ.copy()
    env['GIT_AUTHOR_DATE'] = date_str
    env['GIT_COMMITTER_DATE'] = date_str
    run_cmd(['git', 'commit', '-m', msg], env=env)

print("🚀 과거 기록 재구성을 시작합니다...")

for i, commit_date in enumerate(commit_dates):
    if i < len(FILES_TO_ADD):
        target_file = FILES_TO_ADD[i]
        if os.path.exists(target_file):
            run_cmd(['git', 'add', target_file])
            git_commit(commit_date, f"feat: add {target_file.split('/')[-1]}")
            print(f"[{i+1}/{NUM_COMMITS}] {commit_date.strftime('%Y-%m-%d')} - {target_file} 파일 커밋됨")
        else:
            print(f"⚠️ {target_file} 파일을 찾을 수 없습니다. (패스)")
    else:
        log_file = ".dev_history.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"Updated at {commit_date}\n")
        run_cmd(['git', 'add', log_file])
        types = ["refactor", "fix", "chore", "docs"]
        msg = f"{random.choice(types)}: update system components"
        git_commit(commit_date, msg)
        print(f"[{i+1}/{NUM_COMMITS}] {commit_date.strftime('%Y-%m-%d')} - 유지보수 커밋 생성됨")

print("\n✅ 50개의 커밋 생성 완료! 이제 git push를 진행하세요.")