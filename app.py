import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
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

# 순위 데이터 저장 (메모리)
rankings = []

# 실제 표를 바탕으로 한 MBTI 리스트와 2차원 딕셔너리
MBTIS = [
    'ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
    'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ'
]

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mbti1 = request.form.get('mbti1')   
        mbti2 = request.form.get('mbti2')
        expected_score = request.form.get('expected_score', '')
        nickname = request.form.get('nickname', '')

        # 각 점수 조회 (기본값 50)
        general = COMPAT.get(mbti1, {}).get(mbti2, 50)
        relationship = RELATIONSHIP.get(mbti1, {}).get(mbti2, 50)
        conflict = CONFLICT.get(mbti1, {}).get(mbti2, 50)
        expression = EXPRESSION.get(mbti1, {}).get(mbti2, 50)

        # 최종 점수 계산: (일반 * 2 + 연인관계 + 갈등회복력 + 표현방식) / 5
        final_score = (general * 2 + relationship + conflict + expression) / 5
        score = final_score
        score_display = format_score(final_score)

        # 점수에 따른 단계 결정
        if 90 <= score <= 100:
            stage_emoji = '❤️'
            stage_label = '운명 궁합'
            stage_description = '서로의 장점이 강하게 살아나는 조합이에요. 처음부터 대화가 잘 통하고, 함께 있을수록 에너지가 커질 가능성이 높아요.'
        elif 80 <= score <= 89:
            stage_emoji = '😊'
            stage_label = '찰떡 궁합'
            stage_description = '성향 차이가 있어도 오히려 매력으로 느껴지기 쉬워요. 서로를 존중하면 안정적이고 즐거운 관계가 될 수 있어요.'
        elif 70 <= score <= 79:
            stage_emoji = '🙂'
            stage_label = '좋은 궁합'
            stage_description = '큰 충돌 없이 자연스럽게 가까워질 수 있는 조합이에요. 서로의 다른 점을 이해하면 오래 가기 좋아요.'
        elif 50 <= score <= 69:
            stage_emoji = '😐'
            stage_label = '무난한 궁합'
            stage_description = '특별히 안 맞는 건 아니지만, 엄청난 끌림보다는 천천히 맞춰가는 타입이에요. 대화와 배려가 있으면 충분히 좋은 관계가 될 수 있어요.'
        elif 30 <= score <= 49:
            stage_emoji = '😅'
            stage_label = '유의 궁합'
            stage_description = '친해질 수는 있지만 생각보다 오해가 자주 생길 수 있어요. 감정 표현 방식이나 생활 텐션 차이를 조심해야 해요.'
        elif 10 <= score <= 29:
            stage_emoji = '⚠️'
            stage_label = '충돌 주의 궁합'
            stage_description = '서로의 기준이 많이 달라서 피로감이 쌓이기 쉬워요. 관계를 이어가려면 솔직한 대화와 거리 조절이 중요해요.'
        else:
            stage_emoji = '💔'
            stage_label = '극과 극 궁합'
            stage_description = '강하게 끌릴 수도 있지만, 오래 지내면 성향 차이가 크게 느껴질 수 있어요. 서로를 바꾸려 하기보다 차이를 인정하는 태도가 필요해요.'

        # 예상 점수 변환
        expected_score_float = float(expected_score) if expected_score else 0
        difference = abs(score - expected_score_float)
        
        # 순위 데이터 저장
        current_entry_id = uuid4().hex
        ranking_entry = {
            'id': current_entry_id,
            'nickname': nickname,
            'expected_score': expected_score_float,
            'final_score': score,
            'difference': difference,
            'general': general,
            'relationship': relationship,
            'conflict': conflict,
            'expression': expression
        }
        rankings.insert(0, ranking_entry)
        
        # 최대 100개까지만 유지
        if len(rankings) > 100:
            rankings.pop()

        return render_template('index.html', mbti1=mbti1, mbti2=mbti2,
                               score=score_display, stage_emoji=stage_emoji, stage_label=stage_label,
                               stage_description=stage_description, mbtis=MBTIS, expected_score=expected_score,
                               final_score=final_score, nickname=nickname, rankings=rankings, general=general, relationship=relationship,
                               conflict=conflict, expression=expression, current_entry_id=current_entry_id)
    return render_template('index.html', mbtis=MBTIS, rankings=rankings)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
