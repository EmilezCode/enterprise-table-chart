"""Fixed local transport: personal ACL on the central MCP; no business/UI copies."""
import anyio
import re
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import (CallToolResult,TextContent,ListToolsResult,Tool,
    ListResourcesResult,Resource,ReadResourceResult,TextResourceContents)
from relay_transport import authorized_session,transport_runtime

URI='ui://edp-render-proof/business-daily-v8.html'
# All historic cards resolve to the same current authorized server component.
ALIASES={URI,*('ui://edp-render-proof/'+n+'.html' for n in (
    'business-studio-v9-1','business-studio-v9','business-daily-v7-3','business-daily-v7-2',
    'business-daily-v7-1','business-daily-v7','business-multi-v5','business-readable-v4',
    'business-responsive-v3','business-table-bars-v2'))}
UI_META={'ui':{'resourceUri':URI},'openai/outputTemplate':URI}
# Bounded previous-turn context for follow-ups; mirrors the central service
# schema exactly (no free-form fields, no relaxed validation).
CONTEXT={'type':'object','additionalProperties':False,'properties':{
    'question':{'type':'string','maxLength':2000},
    'chart_unit':{'type':'string','maxLength':40},
    'chart_title':{'type':'string','maxLength':200},
    'chart_labels':{'type':'array','maxItems':60,'items':{'type':'string','maxLength':40}},
    'year_hint':{'type':'string','maxLength':4},
    'tables':{'type':'array','maxItems':6,'items':{'type':'object','additionalProperties':False,
        'properties':{'title':{'type':'string','maxLength':200},
                      'columns':{'type':'array','maxItems':24,'items':{'type':'string','maxLength':40}}}}}}}
SHOW=Tool(name='show_table_chart',title='企业表图',description='当前用户企业MCP的统一表图入口。原自然语言查数，先显示表图，当前Codex再分析。传context可接续上一题：只改展示、补分析或整理报告均不重新查数，继承主体/日期/来源时按上一题明确范围改写问题。其他正式工具可用question="edp-read:"+JSON.stringify({tool:工具名,arguments:原参数})调用；沿游标读取完整后才排名。省略question打开表单。',
    inputSchema={'type':'object','properties':{'question':{'type':'string','minLength':1,'maxLength':2000},'context':CONTEXT},'additionalProperties':False},
    annotations={'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False},
    _meta={**UI_META,'openai/ui':{'entrypoints':[{'type':'global'},{'type':'thread'}]}})

async def tools(context,params):
    try:
        async with authorized_session() as (session,_):listing=await session.list_tools()
    except Exception:
        # The stable entry stays discoverable; a failed service cannot erase it.
        return ListToolsResult(tools=[SHOW])
    current=next((tool for tool in listing.tools if tool.name=='show_table_chart'),SHOW)
    entry=current.model_dump(by_alias=True,exclude_none=True)
    entry['_meta']={**(entry.get('_meta') or {}),'openai/ui':SHOW.meta['openai/ui']}
    exposed=[Tool.model_validate(entry)]
    for tool in listing.tools:
        if tool.name in ('record_render','query_table_chart','complete_table_chart_analysis','get_table_chart_update'):
            exposed.append(tool)
        elif tool.name.startswith('get_') and tool.annotations and tool.annotations.read_only_hint is True:
            declaration=tool.model_dump(by_alias=True,exclude_none=True)
            declaration.pop('outputSchema',None)
            exposed.append(Tool.model_validate(declaration))
    return ListToolsResult(tools=exposed)

async def call(context,params):
    if params.name not in ('show_table_chart','record_render','query_table_chart','complete_table_chart_analysis') and not params.name.startswith('get_'):
        return CallToolResult(isError=True,content=[TextContent(type='text',text='Unknown enterprise read tool.')])
    name=params.name;arguments=params.arguments or {}
    save_kind=None
    if name in ('show_table_chart','query_table_chart') and str(arguments.get('question','')).startswith('edp-ui:save:'):
        save_kind=arguments['question'].split(':',2)[2]
        if save_kind not in ('report','details','summary'):
            return CallToolResult(isError=True,content=[TextContent(type='text',text='未知导出格式。')])
        arguments={**arguments,'question':'edp-ui:file:'+save_kind}
    try:
        async with authorized_session() as (session,_):
            reply=await session.call_tool(name,arguments)
        if save_kind and not reply.is_error:
            from report_download import save_report
            try:
                file=(reply.meta or {}).get('edp/export',{}).get('file')
                saved=save_report(file or {})
                return CallToolResult(structuredContent=saved,
                    content=[TextContent(type='text',text='报告已保存到本机下载目录。')])
            except (OSError,ValueError) as exc:
                return CallToolResult(isError=True,structuredContent={'status':'ERROR',
                    'error':{'code':'FILE_SAVE_FAILED','message':str(exc)}},
                    content=[TextContent(type='text',text='报告保存失败；已查表图保留。')])
        # Only the explicit render entry carries a template. Data calls and
        # paint/analysis receipts must not mount another result card.
        if name=='show_table_chart' and not str(arguments.get('question','')).startswith('edp-ui:'):
            reply.meta=reply.meta or UI_META
        elif name=='query_table_chart' or name=='show_table_chart':
            reply.meta={k:v for k,v in (reply.meta or {}).items() if k not in ('ui','openai/outputTemplate')}
        return reply
    except Exception:
        return CallToolResult(isError=True,structuredContent={'status':'ERROR','is_synthetic':False,
            'error':{'code':'AUTHORIZED_CONNECTION_UNAVAILABLE','message':'企业查询服务暂未连接；已查结果保留，可以稍后继续查询。'}},
            content=[TextContent(type='text',text='企业查询服务暂未连接；不更换来源、不补零。')],
            _meta=UI_META if name=='show_table_chart' else {})

async def resources(context,params):
    return ListResourcesResult(resources=[Resource(uri=URI,name='企业表图',mimeType='text/html;profile=mcp-app')])

async def read(context,params):
    requested=str(params.uri)
    if requested not in ALIASES and re.fullmatch(r'ui://edp-render-proof/business-release-[0-9a-f]{16}\.html',requested) is None:
        raise ValueError('Unknown resource')
    try:
        async with authorized_session() as (session,_):
            response=await session.read_resource(requested)
        # Echo the caller's old alias, while serving the current central HTML.
        for content in response.contents:content.uri=params.uri
        return response
    except Exception:
        # No data/cache/credential in this page; host retry re-reads the service.
        return ReadResourceResult(contents=[TextResourceContents(uri=str(params.uri),mimeType='text/html;profile=mcp-app',
            text='<html lang="zh-CN"><meta charset="utf-8"><body style="font:14px system-ui;padding:24px"><h2>企业查询服务暂未连接</h2><p>已有结果不会被清空。请稍后使用结果卡的重试重新连接，无需重新登录或安装。</p></body></html>',
            _meta={'ui':{'csp':{'connectDomains':[],'resourceDomains':[]}}})])

server=Server('edp-render-proof',version='1.0.0',on_list_tools=tools,on_call_tool=call,on_list_resources=resources,on_read_resource=read,
    instructions='企业表图：所有数据与页面来自当前用户授权的统一企业MCP服务。原结果先展示，当前Codex继续分析；不调用其他模型，不重查已有结果。缺项或未完分页不当零。')

async def main():
    # Starting the local bridge does not wait for a database or network call.
    async with transport_runtime():
        async with stdio_server() as (incoming,outgoing):
            await server.run(incoming,outgoing,server.create_initialization_options())

if __name__=='__main__':anyio.run(main)
