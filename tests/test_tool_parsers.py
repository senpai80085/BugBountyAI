from tools.subfinder import SubfinderTool
from tools.httpx import HttpxTool
from tools.katana import KatanaTool
from tools.naabu import NaabuTool
from tools.nuclei import NucleiTool


def test_subfinder_parser():
    tool = SubfinderTool()
    raw_output = "sub.domain.com\nother.domain.com\n\n"
    res = tool.parse(raw_output)
    assert res == {"subdomains": ["sub.domain.com", "other.domain.com"]}


def test_httpx_parser():
    tool = HttpxTool()
    raw_output = (
        '{"url":"https://domain.com","status_code":200,"title":"Test Title","tech":["Nginx","React"]}\n'
        '{"url":"http://sub.domain.com","status_code":301,"title":"Moved","tech":["Apache"]}'
    )
    res = tool.parse(raw_output)
    endpoints = res["endpoints"]
    assert len(endpoints) == 2
    assert endpoints[0]["url"] == "https://domain.com"
    assert endpoints[0]["status_code"] == 200
    assert endpoints[0]["title"] == "Test Title"
    assert "Nginx" in endpoints[0]["technologies"]
    assert endpoints[1]["status_code"] == 301


def test_katana_parser():
    tool = KatanaTool()
    raw_output = "https://domain.com/about\nhttps://domain.com/contact\n"
    res = tool.parse(raw_output)
    assert res == {"urls": ["https://domain.com/about", "https://domain.com/contact"]}


def test_naabu_parser():
    tool = NaabuTool()
    raw_output = "192.168.1.1:80\n192.168.1.1:443\n"
    res = tool.parse(raw_output)
    ports = res["ports"]
    assert len(ports) == 2
    assert ports[0] == {"host": "192.168.1.1", "port": 80}
    assert ports[1]["port"] == 443


def test_nuclei_parser():
    tool = NucleiTool()
    raw_output = (
        '{"template-id":"git-config","info":{"name":"Git Config Leak","severity":"high","description":"Leak"},"matched-at":"http://target/config"}\n'
        '{"template-id":"http-missing-headers","info":{"name":"Missing Headers","severity":"info"},"host":"target"}'
    )
    res = tool.parse(raw_output)
    vulns = res["vulnerabilities"]
    assert len(vulns) == 2
    assert vulns[0]["template_id"] == "git-config"
    assert vulns[0]["severity"] == "high"
    assert vulns[0]["matched_at"] == "http://target/config"
    assert vulns[1]["severity"] == "info"
