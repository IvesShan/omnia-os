" =============================================================================
" Omnia IDE Bridge - Vim Plugin
" =============================================================================
" 功能：将当前编辑上下文同步到 Omnia AIOS
" 安装：将此目录放入 ~/.vim/pack/omnia/start/
" =============================================================================

if exists('g:omnia_loaded')
    finish
endif
let g:omnia_loaded = 1

" 配置
let g:omnia_host = get(g:, 'omnia_host', '127.0.0.1')
let g:omnia_port = get(g:, 'omnia_port', 5001)
let g:omnia_auto_sync = get(g:, 'omnia_auto_sync', 1)
let g:omnia_sync_interval = get(g:, 'omnia_sync_interval', 1000) " 毫秒

" 发送上下文到 Omnia
function! OmniaSendContext() abort
    let l:file = expand('%:p')
    let l:language = &filetype
    let l:line = line('.')
    let l:column = col('.')
    let l:selected = ''
    
    " 获取选中的文本（如果有）
    if mode() ==# 'v' || mode() ==# 'V'
        let l:selected = getline("'<", "'>")
    endif
    
    " 构建 JSON
    let l:data = {
        \ 'file': l:file,
        \ 'language': l:language,
        \ 'line': l:line,
        \ 'column': l:column,
        \ 'selected': l:selected,
        \ 'timestamp': strftime('%Y-%m-%dT%H:%M:%S')
    \ }
    
    " 发送到 Omnia
    let l:url = printf('http://%s:%d/ide-context', g:omnia_host, g:omnia_port)
    let l:json = json_encode(l:data)
    
    " 使用 curl 发送
    let l:cmd = printf('curl -s -X POST "%s" -H "Content-Type: application/json" -d ''%s'' > /dev/null 2>&1 &',
        \ l:url, l:json)
    call system(l:cmd)
    
    " 更新本地缓存文件
    let l:cache_file = expand('~/.omnia/ide_context.json')
    call writefile([l:json], l:cache_file)
endfunction

" 手动发送命令
command! OmniaSync call OmniaSendContext()

" 自动同步（使用 CursorHold 事件）
if g:omnia_auto_sync
    augroup OmniaAutoSync
        autocmd!
        autocmd CursorHold,CursorHoldI * call OmniaSendContext()
        autocmd BufEnter,BufWrite * call OmniaSendContext()
    augroup END
    
    " 设置 CursorHold 触发时间
    execute 'set updatetime=' . g:omnia_sync_interval
endif

" 显示状态
function! OmniaStatus() abort
    let l:status = printf('[Omnia: %s:%d]', g:omnia_host, g:omnia_port)
    return l:status
endfunction

" 添加到状态栏（可选）
" set statusline+=\ %{OmniaStatus()}

" =============================================================================
" 使用说明
" =============================================================================
" 1. 自动同步：编辑文件时自动发送上下文到 Omnia
" 2. 手动同步：:OmniaSync
" 3. 配置选项：
"    let g:omnia_host = '127.0.0.1'
"    let g:omnia_port = 5001
"    let g:omnia_auto_sync = 1
" =============================================================================
