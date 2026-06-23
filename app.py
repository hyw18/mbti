import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import venv


PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / '.venv'
REQUIRED_PACKAGES = ('Flask>=2.2.0',)


def running_in_venv():
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)


def venv_python():
    if os.name == 'nt':
        return VENV_DIR / 'Scripts' / 'python.exe'
    return VENV_DIR / 'bin' / 'python'

def install_packages(python_executable):
    subprocess.check_call([str(python_executable), '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([str(python_executable), '-m', 'pip', 'install', *REQUIRED_PACKAGES])


def ensure_direct_run_environment():
    """직접 실행할 때만 예전 setup_venv.sh 동작을 수행한다."""
    if running_in_venv():
        if importlib.util.find_spec('flask') is None:
            install_packages(Path(sys.executable))
        return

    python_executable = venv_python()
    if not python_executable.exists():
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
        print('가상환경 .venv 생성됨')

    check = subprocess.run(
        [str(python_executable), '-c', 'import flask'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if check.returncode != 0:
        install_packages(python_executable)
        print('설치 완료. 가상환경 활성화: source .venv/bin/activate')

    os.execv(str(python_executable), [str(python_executable), *sys.argv])


if __name__ == '__main__':
    ensure_direct_run_environment()

from flask import Flask, render_template, request

app = Flask(__name__, static_folder='static', static_url_path='/static')

# 실제 표를 바탕으로 한 MBTI 리스트와 2차원 딕셔너리
MBTIS = [
    'ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
    'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ'
]

GENDER_WEIGHTS = {
    'male-male': {
        'compatibility': 0.40,
        'duration': 0.24,
        'recovery': 0.19,
        'expression': 0.17,
    },
    'male-female': {
        'compatibility': 0.40,
        'duration': 0.23,
        'recovery': 0.19,
        'expression': 0.18,
    },
    'male-none': {
        'compatibility': 0.40,
        'duration': 0.24,
        'recovery': 0.19,
        'expression': 0.17,
    },
    'female-male': {
        'compatibility': 0.40,
        'duration': 0.22,
        'recovery': 0.20,
        'expression': 0.18,
    },
    'female-female': {
        'compatibility': 0.40,
        'duration': 0.21,
        'recovery': 0.20,
        'expression': 0.19,
    },
    'female-none': {
        'compatibility': 0.40,
        'duration': 0.22,
        'recovery': 0.20,
        'expression': 0.18,
    },
}

VALID_MY_GENDERS = {'male', 'female'}
VALID_PARTNER_GENDERS = {'male', 'female', 'none'}

SCORE_GROUPS = (
    {
        'label': '90점 이상',
        'title': '최상 궁합',
        'description': '대화, 안정감, 표현 방식이 고르게 잘 맞아 자연스럽게 가까워지기 좋아요.',
        'color_class': 'score-blue',
        'min_score': 90,
        'max_score': None,
    },
    {
        'label': '80점 이상',
        'title': '좋은 궁합',
        'description': '큰 흐름이 잘 맞고 관계를 이어갈 때 부담이 비교적 적은 편이에요.',
        'color_class': 'score-mint',
        'min_score': 80,
        'max_score': 90,
    },
    {
        'label': '65점 이상',
        'title': '무난한 궁합',
        'description': '기본 궁합은 괜찮지만 서로의 차이를 알고 맞춰가면 더 좋아져요.',
        'color_class': 'score-green',
        'min_score': 65,
        'max_score': 80,
    },
    {
        'label': '50점 이상',
        'title': '조율 필요',
        'description': '관계가 좋아지려면 대화 방식과 갈등 해결 습관을 의식적으로 맞춰야 해요.',
        'color_class': 'score-yellow',
        'min_score': 50,
        'max_score': 65,
    },
    {
        'label': '30점 이상',
        'title': '주의 필요',
        'description': '서로의 기준이 달라 오해가 쌓이기 쉬우니 천천히 확인하는 편이 좋아요.',
        'color_class': 'score-red',
        'min_score': 30,
        'max_score': 50,
    },
    {
        'label': '30점 미만',
        'title': '거리 조절 필요',
        'description': '성향 차이가 크게 느껴질 수 있어 관계 속도를 아주 천천히 잡는 편이 좋아요.',
        'color_class': 'score-purple-dark',
        'min_score': 0,
        'max_score': 30,
    },
)

# 실제 표를 바탕으로 한 2차원 딕셔너리 (행: 나, 열: 상대)
COMPAT = {
    'ISTJ': {'ISTJ':62,'ISFJ':78,'INFJ':44,'INTJ':68,'ISTP':54,'ISFP':42,'INFP':28,'INTP':38,'ESTP':35,'ESFP':30,'ENFP':18,'ENTP':26,'ESTJ':88,'ESFJ':84,'ENFJ':36,'ENTJ':76},
    'ISFJ': {'ISTJ':78,'ISFJ':66,'INFJ':70,'INTJ':40,'ISTP':38,'ISFP':72,'INFP':56,'INTP':24,'ESTP':28,'ESFP':74,'ENFP':46,'ENTP':18,'ESTJ':82,'ESFJ':92,'ENFJ':86,'ENTJ':42},
    'INFJ': {'ISTJ':44,'ISFJ':70,'INFJ':64,'INTJ':82,'ISTP':22,'ISFP':60,'INFP':88,'INTP':76,'ESTP':14,'ESFP':48,'ENFP':96,'ENTP':90,'ESTJ':18,'ESFJ':78,'ENFJ':94,'ENTJ':84},
    'INTJ': {'ISTJ':68,'ISFJ':40,'INFJ':82,'INTJ':66,'ISTP':72,'ISFP':26,'INFP':70,'INTP':88,'ESTP':46,'ESFP':16,'ENFP':78,'ENTP':96,'ESTJ':74,'ESFJ':20,'ENFJ':64,'ENTJ':92},
    'ISTP': {'ISTJ':54,'ISFJ':38,'INFJ':22,'INTJ':72,'ISTP':60,'ISFP':84,'INFP':34,'INTP':86,'ESTP':92,'ESFP':74,'ENFP':50,'ENTP':78,'ESTJ':66,'ESFJ':32,'ENFJ':20,'ENTJ':74},
    'ISFP': {'ISTJ':42,'ISFJ':72,'INFJ':60,'INTJ':26,'ISTP':84,'ISFP':62,'INFP':86,'INTP':36,'ESTP':74,'ESFP':90,'ENFP':94,'ENTP':52,'ESTJ':18,'ESFJ':82,'ENFJ':92,'ENTJ':28},
    'INFP': {'ISTJ':28,'ISFJ':56,'INFJ':88,'INTJ':70,'ISTP':34,'ISFP':86,'INFP':68,'INTP':82,'ESTP':20,'ESFP':64,'ENFP':98,'ENTP':90,'ESTJ':8,'ESFJ':58,'ENFJ':96,'ENTJ':72},
    'INTP': {'ISTJ':38,'ISFJ':24,'INFJ':76,'INTJ':88,'ISTP':86,'ISFP':36,'INFP':82,'INTP':64,'ESTP':62,'ESFP':22,'ENFP':84,'ENTP':94,'ESTJ':32,'ESFJ':16,'ENFJ':68,'ENTJ':98},
    'ESTP': {'ISTJ':35,'ISFJ':28,'INFJ':14,'INTJ':46,'ISTP':92,'ISFP':74,'INFP':20,'INTP':62,'ESTP':66,'ESFP':94,'ENFP':76,'ENTP':88,'ESTJ':72,'ESFJ':36,'ENFJ':30,'ENTJ':82},
    'ESFP': {'ISTJ':30,'ISFJ':74,'INFJ':48,'INTJ':16,'ISTP':88,'ISFP':90,'INFP':64,'INTP':22,'ESTP':94,'ESFP':68,'ENFP':92,'ENTP':72,'ESTJ':36,'ESFJ':88,'ENFJ':84,'ENTJ':38},
    'ENFP': {'ISTJ':18,'ISFJ':46,'INFJ':96,'INTJ':78,'ISTP':50,'ISFP':94,'INFP':98,'INTP':84,'ESTP':76,'ESFP':68,'ENFP':92,'ENTP':92,'ESTJ':22,'ESFJ':62,'ENFJ':100,'ENTJ':80},
    'ENTP': {'ISTJ':26,'ISFJ':18,'INFJ':90,'INTJ':96,'ISTP':78,'ISFP':52,'INFP':90,'INTP':94,'ESTP':88,'ESFP':72,'ENFP':92,'ENTP':68,'ESTJ':56,'ESFJ':24,'ENFJ':86,'ENTJ':100},
    'ESTJ': {'ISTJ':88,'ISFJ':82,'INFJ':18,'INTJ':74,'ISTP':66,'ISFP':18,'INFP':8,'INTP':32,'ESTP':72,'ESFP':36,'ENFP':22,'ENTP':56,'ESTJ':64,'ESFJ':86,'ENFJ':38,'ENTJ':94},
    'ESFJ': {'ISTJ':84,'ISFJ':92,'INFJ':78,'INTJ':20,'ISTP':32,'ISFP':82,'INFP':58,'INTP':16,'ESTP':50,'ESFP':88,'ENFP':62,'ENTP':24,'ESTJ':86,'ESFJ':66,'ENFJ':90,'ENTJ':44},
    'ENFJ': {'ISTJ':36,'ISFJ':86,'INFJ':94,'INTJ':64,'ISTP':20,'ISFP':92,'INFP':96,'INTP':68,'ESTP':30,'ESFP':84,'ENFP':100,'ENTP':86,'ESTJ':38,'ESFJ':90,'ENFJ':72,'ENTJ':82},
    'ENTJ': {'ISTJ':76,'ISFJ':42,'INFJ':84,'INTJ':92,'ISTP':74,'ISFP':28,'INFP':72,'INTP':98,'ESTP':82,'ESFP':38,'ENFP':80,'ENTP':100,'ESTJ':94,'ESFJ':44,'ENFJ':82,'ENTJ':70},
}

# 연인 관계 지속시간 점수
RELATIONSHIP = {
    'ISTJ': {'ISTJ':82,'ISFJ':90,'INFJ':58,'INTJ':76,'ISTP':66,'ISFP':60,'INFP':42,'INTP':52,'ESTP':48,'ESFP':42,'ENFP':30,'ENTP':38,'ESTJ':94,'ESFJ':88,'ENFJ':50,'ENTJ':84},
    'ISFJ': {'ISTJ':90,'ISFJ':86,'INFJ':82,'INTJ':54,'ISTP':56,'ISFP':84,'INFP':72,'INTP':40,'ESTP':38,'ESFP':78,'ENFP':60,'ENTP':32,'ESTJ':86,'ESFJ':96,'ENFJ':86,'ENTJ':56},
    'INFJ': {'ISTJ':58,'ISFJ':82,'INFJ':78,'INTJ':88,'ISTP':36,'ISFP':74,'INFP':90,'INTP':80,'ESTP':24,'ESFP':58,'ENFP':92,'ENTP':84,'ESTJ':30,'ESFJ':84,'ENFJ':94,'ENTJ':72},
    'INTJ': {'ISTJ':76,'ISFJ':54,'INFJ':88,'INTJ':84,'ISTP':78,'ISFP':38,'INFP':78,'INTP':92,'ESTP':56,'ESFP':28,'ENFP':76,'ENTP':90,'ESTJ':82,'ESFJ':32,'ENFJ':72,'ENTJ':82},
    'ISTP': {'ISTJ':66,'ISFJ':56,'INFJ':36,'INTJ':78,'ISTP':76,'ISFP':88,'INFP':46,'INTP':84,'ESTP':86,'ESFP':82,'ENFP':58,'ENTP':76,'ESTJ':72,'ESFJ':48,'ENFJ':34,'ENTJ':80},
    'ISFP': {'ISTJ':60,'ISFJ':84,'INFJ':74,'INTJ':38,'ISTP':88,'ISFP':78,'INFP':88,'INTP':50,'ESTP':70,'ESFP':86,'ENFP':84,'ENTP':58,'ESTJ':32,'ESFJ':88,'ENFJ':90,'ENTJ':40},
    'INFP': {'ISTJ':42,'ISFJ':72,'INFJ':90,'INTJ':78,'ISTP':46,'ISFP':88,'INFP':76,'INTP':82,'ESTP':30,'ESFP':68,'ENFP':86,'ENTP':78,'ESTJ':14,'ESFJ':74,'ENFJ':92,'ENTJ':74},
    'INTP': {'ISTJ':52,'ISFJ':40,'INFJ':80,'INTJ':92,'ISTP':84,'ISFP':50,'INFP':82,'INTP':78,'ESTP':64,'ESFP':36,'ENFP':78,'ENTP':88,'ESTJ':46,'ESFJ':28,'ENFJ':70,'ENTJ':94},
    'ESTP': {'ISTJ':48,'ISFJ':38,'INFJ':24,'INTJ':56,'ISTP':86,'ISFP':70,'INFP':30,'INTP':64,'ESTP':74,'ESFP':82,'ENFP':72,'ENTP':84,'ESTJ':78,'ESFJ':58,'ENFJ':36,'ENTJ':78},
    'ESFP': {'ISTJ':42,'ISFJ':78,'INFJ':58,'INTJ':28,'ISTP':82,'ISFP':86,'INFP':68,'INTP':36,'ESTP':82,'ESFP':76,'ENFP':84,'ENTP':70,'ESTJ':52,'ESFJ':90,'ENFJ':82,'ENTJ':70},
    'ENFP': {'ISTJ':30,'ISFJ':60,'INFJ':92,'INTJ':76,'ISTP':58,'ISFP':84,'INFP':86,'INTP':78,'ESTP':72,'ESFP':84,'ENFP':74,'ENTP':82,'ESTJ':34,'ESFJ':76,'ENFJ':100,'ENTJ':78},
    'ENTP': {'ISTJ':38,'ISFJ':32,'INFJ':84,'INTJ':90,'ISTP':76,'ISFP':58,'INFP':78,'INTP':88,'ESTP':84,'ESFP':70,'ENFP':82,'ENTP':72,'ESTJ':66,'ESFJ':30,'ENFJ':82,'ENTJ':72},
    'ESTJ': {'ISTJ':94,'ISFJ':86,'INFJ':30,'INTJ':82,'ISTP':72,'ISFP':32,'INFP':14,'INTP':46,'ESTP':78,'ESFP':52,'ENFP':32,'ENTP':64,'ESTJ':78,'ESFJ':88,'ENFJ':52,'ENTJ':94},
    'ESFJ': {'ISTJ':88,'ISFJ':96,'INFJ':84,'INTJ':32,'ISTP':48,'ISFP':88,'INFP':70,'INTP':28,'ESTP':56,'ESFP':90,'ENFP':72,'ENTP':38,'ESTJ':88,'ESFJ':86,'ENFJ':94,'ENTJ':54},
    'ENFJ': {'ISTJ':50,'ISFJ':86,'INFJ':94,'INTJ':72,'ISTP':34,'ISFP':90,'INFP':92,'INTP':70,'ESTP':42,'ESFP':82,'ENFP':94,'ENTP':82,'ESTJ':54,'ESFJ':94,'ENFJ':82,'ENTJ':54},
    'ENTJ': {'ISTJ':84,'ISFJ':56,'INFJ':72,'INTJ':82,'ISTP':80,'ISFP':40,'INFP':74,'INTP':94,'ESTP':80,'ESFP':50,'ENFP':78,'ENTP':98,'ESTJ':96,'ESFJ':54,'ENFJ':82,'ENTJ':84},
}

# 갈등 회복력 점수
CONFLICT = {
    'ISTJ': {'ISTJ':76,'ISFJ':86,'INFJ':58,'INTJ':74,'ISTP':64,'ISFP':56,'INFP':38,'INTP':52,'ESTP':46,'ESFP':40,'ENFP':28,'ENTP':36,'ESTJ':92,'ESFJ':84,'ENFJ':50,'ENTJ':82},
    'ISFJ': {'ISTJ':86,'ISFJ':82,'INFJ':84,'INTJ':52,'ISTP':54,'ISFP':82,'INFP':72,'INTP':38,'ESTP':36,'ESFP':76,'ENFP':62,'ENTP':30,'ESTJ':84,'ESFJ':94,'ENFJ':90,'ENTJ':56},
    'INFJ': {'ISTJ':58,'ISFJ':84,'INFJ':78,'INTJ':88,'ISTP':34,'ISFP':76,'INFP':92,'INTP':82,'ESTP':22,'ESFP':60,'ENFP':94,'ENTP':86,'ESTJ':28,'ESFJ':88,'ENFJ':96,'ENTJ':84},
    'INTJ': {'ISTJ':74,'ISFJ':52,'INFJ':88,'INTJ':80,'ISTP':78,'ISFP':36,'INFP':76,'INTP':92,'ESTP':54,'ESFP':26,'ENFP':74,'ENTP':90,'ESTJ':82,'ESFJ':32,'ENFJ':70,'ENTJ':94},
    'ISTP': {'ISTJ':64,'ISFJ':54,'INFJ':34,'INTJ':78,'ISTP':72,'ISFP':84,'INFP':44,'INTP':86,'ESTP':84,'ESFP':80,'ENFP':56,'ENTP':78,'ESTJ':70,'ESFJ':46,'ENFJ':32,'ENTJ':76},
    'ISFP': {'ISTJ':56,'ISFJ':82,'INFJ':76,'INTJ':36,'ISTP':84,'ISFP':76,'INFP':90,'INTP':48,'ESTP':68,'ESFP':84,'ENFP':88,'ENTP':56,'ESTJ':30,'ESFJ':86,'ENFJ':92,'ENTJ':38},
    'INFP': {'ISTJ':38,'ISFJ':72,'INFJ':92,'INTJ':76,'ISTP':44,'ISFP':90,'INFP':74,'INTP':84,'ESTP':28,'ESFP':66,'ENFP':90,'ENTP':82,'ESTJ':12,'ESFJ':70,'ENFJ':94,'ENTJ':72},
    'INTP': {'ISTJ':52,'ISFJ':38,'INFJ':82,'INTJ':92,'ISTP':86,'ISFP':48,'INFP':84,'INTP':76,'ESTP':62,'ESFP':34,'ENFP':80,'ENTP':88,'ESTJ':44,'ESFJ':26,'ENFJ':68,'ENTJ':92},
    'ESTP': {'ISTJ':46,'ISFJ':36,'INFJ':22,'INTJ':54,'ISTP':84,'ISFP':68,'INFP':28,'INTP':62,'ESTP':72,'ESFP':82,'ENFP':70,'ENTP':86,'ESTJ':76,'ESFJ':54,'ENFJ':40,'ENTJ':82},
    'ESFP': {'ISTJ':40,'ISFJ':76,'INFJ':60,'INTJ':26,'ISTP':80,'ISFP':84,'INFP':66,'INTP':34,'ESTP':82,'ESFP':74,'ENFP':86,'ENTP':70,'ESTJ':50,'ESFJ':88,'ENFJ':84,'ENTJ':48},
    'ENFP': {'ISTJ':28,'ISFJ':62,'INFJ':94,'INTJ':74,'ISTP':56,'ISFP':88,'INFP':90,'INTP':80,'ESTP':70,'ESFP':86,'ENFP':76,'ENTP':84,'ESTJ':32,'ESFJ':72,'ENFJ':98,'ENTJ':78},
    'ENTP': {'ISTJ':36,'ISFJ':30,'INFJ':86,'INTJ':90,'ISTP':78,'ISFP':56,'INFP':82,'INTP':88,'ESTP':86,'ESFP':70,'ENFP':84,'ENTP':74,'ESTJ':64,'ESFJ':38,'ENFJ':82,'ENTJ':96},
    'ESTJ': {'ISTJ':92,'ISFJ':84,'INFJ':28,'INTJ':82,'ISTP':70,'ISFP':30,'INFP':12,'INTP':44,'ESTP':76,'ESFP':50,'ENFP':32,'ENTP':64,'ESTJ':78,'ESFJ':88,'ENFJ':52,'ENTJ':94},
    'ESFJ': {'ISTJ':84,'ISFJ':94,'INFJ':88,'INTJ':32,'ISTP':46,'ISFP':86,'INFP':70,'INTP':26,'ESTP':54,'ESFP':88,'ENFP':72,'ENTP':38,'ESTJ':88,'ESFJ':66,'ENFJ':90,'ENTJ':58},
    'ENFJ': {'ISTJ':50,'ISFJ':90,'INFJ':96,'INTJ':70,'ISTP':32,'ISFP':92,'INFP':94,'INTP':68,'ESTP':40,'ESFP':84,'ENFP':98,'ENTP':82,'ESTJ':52,'ESFJ':90,'ENFJ':72,'ENTJ':86},
    'ENTJ': {'ISTJ':82,'ISFJ':56,'INFJ':84,'INTJ':94,'ISTP':76,'ISFP':38,'INFP':72,'INTP':92,'ESTP':82,'ESFP':48,'ENFP':78,'ENTP':96,'ESTJ':94,'ESFJ':58,'ENFJ':86,'ENTJ':80},
}

# 표현 방식 일치도 점수
EXPRESSION = {
    'ISTJ': {'ISTJ':78,'ISFJ':88,'INFJ':52,'INTJ':72,'ISTP':62,'ISFP':50,'INFP':34,'INTP':48,'ESTP':44,'ESFP':36,'ENFP':24,'ENTP':32,'ESTJ':90,'ESFJ':86,'ENFJ':46,'ENTJ':80},
    'ISFJ': {'ISTJ':88,'ISFJ':84,'INFJ':78,'INTJ':46,'ISTP':50,'ISFP':86,'INFP':70,'INTP':32,'ESTP':34,'ESFP':82,'ENFP':60,'ENTP':26,'ESTJ':82,'ESFJ':96,'ENFJ':88,'ENTJ':50},
    'INFJ': {'ISTJ':52,'ISFJ':78,'INFJ':82,'INTJ':76,'ISTP':28,'ISFP':74,'INFP':94,'INTP':72,'ESTP':18,'ESFP':56,'ENFP':92,'ENTP':80,'ESTJ':22,'ESFJ':84,'ENFJ':98,'ENTJ':78},
    'INTJ': {'ISTJ':72,'ISFJ':46,'INFJ':76,'INTJ':74,'ISTP':80,'ISFP':30,'INFP':66,'INTP':88,'ESTP':58,'ESFP':20,'ENFP':68,'ENTP':86,'ESTJ':78,'ESFJ':28,'ENFJ':62,'ENTJ':92},
    'ISTP': {'ISTJ':62,'ISFJ':50,'INFJ':28,'INTJ':80,'ISTP':76,'ISFP':82,'INFP':40,'INTP':84,'ESTP':90,'ESFP':86,'ENFP':54,'ENTP':82,'ESTJ':70,'ESFJ':42,'ENFJ':26,'ENTJ':78},
    'ISFP': {'ISTJ':50,'ISFJ':86,'INFJ':74,'INTJ':30,'ISTP':82,'ISFP':84,'INFP':92,'INTP':44,'ESTP':76,'ESFP':94,'ENFP':96,'ENTP':60,'ESTJ':24,'ESFJ':90,'ENFJ':94,'ENTJ':34},
    'INFP': {'ISTJ':34,'ISFJ':70,'INFJ':94,'INTJ':66,'ISTP':40,'ISFP':92,'INFP':86,'INTP':76,'ESTP':24,'ESFP':72,'ENFP':98,'ENTP':84,'ESTJ':8,'ESFJ':74,'ENFJ':100,'ENTJ':68},
    'INTP': {'ISTJ':48,'ISFJ':32,'INFJ':72,'INTJ':88,'ISTP':84,'ISFP':44,'INFP':76,'INTP':78,'ESTP':66,'ESFP':28,'ENFP':80,'ENTP':92,'ESTJ':38,'ESFJ':22,'ENFJ':64,'ENTJ':94},
    'ESTP': {'ISTJ':44,'ISFJ':34,'INFJ':18,'INTJ':58,'ISTP':90,'ISFP':76,'INFP':24,'INTP':66,'ESTP':82,'ESFP':96,'ENFP':78,'ENTP':90,'ESTJ':74,'ESFJ':58,'ENFJ':36,'ENTJ':84},
    'ESFP': {'ISTJ':36,'ISFJ':82,'INFJ':56,'INTJ':20,'ISTP':86,'ISFP':94,'INFP':72,'INTP':28,'ESTP':96,'ESFP':88,'ENFP':94,'ENTP':76,'ESTJ':42,'ESFJ':92,'ENFJ':90,'ENTJ':46},
    'ENFP': {'ISTJ':24,'ISFJ':60,'INFJ':92,'INTJ':68,'ISTP':54,'ISFP':96,'INFP':98,'INTP':80,'ESTP':78,'ESFP':94,'ENFP':88,'ENTP':94,'ESTJ':28,'ESFJ':76,'ENFJ':100,'ENTJ':78},
    'ENTP': {'ISTJ':32,'ISFJ':26,'INFJ':80,'INTJ':86,'ISTP':82,'ISFP':60,'INFP':84,'INTP':92,'ESTP':90,'ESFP':76,'ENFP':94,'ENTP':86,'ESTJ':58,'ESFJ':30,'ENFJ':84,'ENTJ':98},
    'ESTJ': {'ISTJ':90,'ISFJ':82,'INFJ':22,'INTJ':78,'ISTP':70,'ISFP':24,'INFP':8,'INTP':38,'ESTP':74,'ESFP':42,'ENFP':28,'ENTP':58,'ESTJ':80,'ESFJ':88,'ENFJ':44,'ENTJ':96},
    'ESFJ': {'ISTJ':86,'ISFJ':96,'INFJ':84,'INTJ':28,'ISTP':42,'ISFP':90,'INFP':74,'INTP':22,'ESTP':58,'ESFP':92,'ENFP':76,'ENTP':30,'ESTJ':88,'ESFJ':86,'ENFJ':94,'ENTJ':54},
    'ENFJ': {'ISTJ':46,'ISFJ':88,'INFJ':98,'INTJ':62,'ISTP':26,'ISFP':94,'INFP':100,'INTP':64,'ESTP':36,'ESFP':90,'ENFP':100,'ENTP':84,'ESTJ':44,'ESFJ':94,'ENFJ':82,'ENTJ':82},
    'ENTJ': {'ISTJ':80,'ISFJ':50,'INFJ':78,'INTJ':92,'ISTP':78,'ISFP':34,'INFP':68,'INTP':94,'ESTP':84,'ESFP':46,'ENFP':78,'ENTP':98,'ESTJ':96,'ESFJ':54,'ENFJ':82,'ENTJ':84},
}

def format_score(score):
    """소수점 처리: 둘째 자리까지만 표시, 소수점이 없으면 표시 안함, 한 자리면 한 자리만 표시"""
    if score == int(score):
        return str(int(score))
    rounded = round(score, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    formatted = f"{rounded:.2f}".rstrip('0')
    return formatted


def calculate_final_score(scores, my_gender, partner_gender):
    relation_key = f'{my_gender}-{partner_gender}'
    weights = GENDER_WEIGHTS.get(relation_key)
    if weights is None:
        raise ValueError('올바르지 않은 성별 선택값입니다.')

    return (
        scores['compatibility'] * weights['compatibility']
        + scores['duration'] * weights['duration']
        + scores['recovery'] * weights['recovery']
        + scores['expression'] * weights['expression']
    )


def get_score_stage(score):
    if score >= 90:
        return '최상 궁합'
    if score >= 80:
        return '좋은 궁합'
    if score >= 65:
        return '무난한 궁합'
    if score >= 50:
        return '조율이 필요한 궁합'
    if score >= 30:
        return '주의가 필요한 궁합'
    return '거리 조절이 필요한 궁합'


def get_result_description(score):
    if score >= 90:
        return '서로의 강점이 자연스럽게 맞물려 안정감과 설렘을 함께 기대할 수 있어요.'
    if score >= 80:
        return '큰 흐름이 잘 맞는 편이라 대화와 생활 리듬을 맞추기 수월해요.'
    if score >= 65:
        return '기본 궁합은 괜찮지만 표현 방식과 갈등 해결 습관을 맞추면 더 좋아져요.'
    if score >= 50:
        return '관계가 굴러가려면 서로의 차이를 의식적으로 조율하는 과정이 필요해요.'
    if score >= 30:
        return '끌림과 별개로 반복되는 오해가 생기기 쉬워 천천히 확인하는 편이 좋아요.'
    return '관계 속도를 늦추고 서로의 기준을 충분히 확인하는 과정이 필요해요.'


def build_match_result(my_mbti, other_mbti, my_gender, partner_gender):
    general = COMPAT[my_mbti][other_mbti]
    relationship = RELATIONSHIP[my_mbti][other_mbti]
    conflict = CONFLICT[my_mbti][other_mbti]
    expression = EXPRESSION[my_mbti][other_mbti]
    scores = {
        'compatibility': general,
        'duration': relationship,
        'recovery': conflict,
        'expression': expression,
    }
    total = calculate_final_score(scores, my_gender, partner_gender)
    return {
        'mbti': other_mbti,
        'total': total,
        'total_display': format_score(total),
        'stage': get_score_stage(total),
        'description': get_result_description(total),
        'general': general,
        'relationship': relationship,
        'conflict': conflict,
        'expression': expression,
    }


def add_factor_highlights(matches):
    factor_keys = ('general', 'relationship', 'conflict', 'expression')
    factor_ranges = {
        key: {
            'max': max(match[key] for match in matches),
            'min': min(match[key] for match in matches),
        }
        for key in factor_keys
    }

    for match in matches:
        match['factor_highlights'] = {}
        for key in factor_keys:
            if match[key] == factor_ranges[key]['max']:
                match['factor_highlights'][key] = 'factor-high'
            elif match[key] == factor_ranges[key]['min']:
                match['factor_highlights'][key] = 'factor-low'
            else:
                match['factor_highlights'][key] = ''


def group_matches_by_score(matches):
    groups = []
    for score_group in SCORE_GROUPS:
        group_matches = [
            match
            for match in matches
            if match['total'] >= score_group['min_score']
            and (score_group['max_score'] is None or match['total'] < score_group['max_score'])
        ]
        groups.append({**score_group, 'matches': group_matches})
    return groups


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        my_mbti = request.form.get('my_mbti', '').upper()
        my_gender = request.form.get('myGender', '')
        partner_gender = request.form.get('partnerGender', 'none')
        if partner_gender not in VALID_PARTNER_GENDERS:
            partner_gender = 'none'

        if my_mbti not in MBTIS:
            return render_template('index.html', mbtis=MBTIS, error='올바른 MBTI를 선택해주세요.'), 400
        if my_gender not in VALID_MY_GENDERS:
            return render_template(
                'index.html',
                mbtis=MBTIS,
                error='본인 성별을 선택해주세요.',
                selected_mbti=my_mbti,
                selected_partner_gender=partner_gender,
            ), 400

        matches = [
            build_match_result(my_mbti, other_mbti, my_gender, partner_gender)
            for other_mbti in MBTIS
        ]
        add_factor_highlights(matches)
        matches.sort(key=lambda match: (-match['total'], match['mbti']))
        for rank, match in enumerate(matches, start=1):
            match['rank'] = rank

        return render_template(
            'index.html',
            mbtis=MBTIS,
            my_mbti=my_mbti,
            match_groups=group_matches_by_score(matches),
        )
    return render_template('index.html', mbtis=MBTIS)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
