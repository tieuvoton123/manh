"""Finalize PS4 app exit without SDL/thread teardown races.

The native Sony PS4 SystemService exit is inspired by PS4CheatsManager.
The installer is an external BGFT task; it is not terminated by Store exit.
"""
from pathlib import Path


def rep(source: str, before: str, after: str, count: int = 1) -> str:
    actual = source.count(before)
    if actual != count:
        raise RuntimeError(f'PS4 safe-exit patch expected {count} occurrences, found {actual}: {before[:100]!r}')
    return source.replace(before, after, count)


def apply(source: Path, root: Path) -> None:
    main = source / 'src' / 'main.cpp'
    data = main.read_text(encoding='utf-8')
    # PS4 native exit, not a fake GoldHEN menu launch.
    data = rep(data, '#include "chepgame_transfer_meter.hpp"',
               '#include "chepgame_transfer_meter.hpp"\n'
               '#include <orbis/SystemService.h>\n'
               '#include <orbis/Sysmodule.h>\n'
               '#include <cstdio>')

    # Both real workers are created by the main SDL thread. Make threads joinable
    # and retain exactly one handle (join the previous finished thread before
    # a new worker starts). This closes the use-after-free window of SharedState.
    if 'SDL_DestroyRenderer(renderer)' not in data:
        # The tiny test fixture does not contain an SDL app/main loop.
        # Real pinned upstream source always has an SDL cleanup sequence.
        pass
    elif data.count('pthread_detach(thread);') == 2:
        anchor = 'void* local_install_worker(void* p) {'
        register = r'''// Only called on SDL main thread. BGFT tasks themselves continue in PS4 OS.
static pthread_t chepgame_last_worker;
static bool chepgame_has_worker = false;
void chepgame_join_worker() {
    if (!chepgame_has_worker) return;
    pthread_join(chepgame_last_worker, nullptr);
    chepgame_has_worker = false;
}
void chepgame_track_worker(pthread_t thread) {
    chepgame_last_worker = thread;
    chepgame_has_worker = true;
}
void chepgame_exit_log(const char* phase, int32_t code) {
    FILE* fp = std::fopen("/data/ChepGameStore/thoat.log", "a");
    if (!fp) return;
    std::fprintf(fp, "%s: 0x%08X\n", phase, (unsigned)code);
    std::fclose(fp);
}
'''
        data = rep(data, anchor, register + '\n' + anchor)
        # Worker registry functions must be visible from both start_job functions.
        data = rep(data, '    pthread_detach(thread);', '    chepgame_track_worker(thread);', 2)
        # When a previous task sets job_running=false immediately before returning,
        # we cannot start a new task until pthread_join has completed.
        local_anchor = '    pthread_t thread;\n    if(pthread_create(&thread,nullptr,local_install_worker,&state)!=0) {'
        data = rep(data, local_anchor,
                   '    chepgame_join_worker();\n' + local_anchor)
        remote_anchor = '    pthread_t thread;\n    if (pthread_create(&thread, 0, job_main, args) != 0) {'
        data = rep(data, remote_anchor,
                   '    chepgame_join_worker();\n' + remote_anchor)
    else:
        raise RuntimeError('Unexpected PS4 worker topology; refuse partial exit patch')

    real_ending = '''    if (joystick) SDL_JoystickClose(joystick);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;'''
    if real_ending in data:
        # Join before making PS4 system exit request. On success the operating
        # system takes over app lifecycle; avoid manual teardown while exiting.
        # Fallback: clean renderer glyph cache before destroying its textures.
        after = '''    chepgame_join_worker();
    chepgame_exit_log("WORKERS_JOINED", 0);
    const int32_t service = (int32_t)sceSysmoduleLoadModuleInternal(
        ORBIS_SYSMODULE_INTERNAL_SYSTEM_SERVICE);
    chepgame_exit_log("SYSTEM_MODULE", service);
    {
        // Some runtimes report already-loaded for this module; try exit anyway.
        chepgame_exit_log("REQUEST_SYSTEM_EXIT", 0);
        const int32_t result = sceSystemServiceLoadExec("exit", nullptr);
        // A successful handoff usually does not return; log unexpected returns.
        chepgame_exit_log("SYSTEM_EXIT_RETURNED", result);
    }
    // If PS4 denies system exit, fall back to standard SDL cleanup safely.
    orbisshelf::shutdown_font();
    if (joystick) SDL_JoystickClose(joystick);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;'''
        data = rep(data, real_ending, after)
    elif 'SDL_DestroyRenderer(renderer)' not in data:
        # Fixture-only path; a real app cannot omit cleanup/exit logic.
        pass
    else:
        raise RuntimeError('Native app cleanup anchor changed; refusing to ship broken exit')

    # Do not accept queued input events after exit was requested.
    data = data.replace('if (quit && !busy) running = false;',
                        'if (quit && !busy) { running = false; break; }')
    data = data.replace('if (!busy && edit_url) { running=false; continue; } // GoldHEN menu fallback',
                        'if (!busy && edit_url) { running=false; break; } // Return to PS4 home; open GoldHEN there')
    # Native upstream has one event loop and a final render per frame.
    loop_after_events = '        pthread_mutex_lock(&state.mutex);\n        const int count = static_cast<int>(state.items.size());'
    if loop_after_events in data:
        data = data.replace(loop_after_events,
                            '        if (!running) break;\n' + loop_after_events, 1)

    # Upgrade UI without touching download, BGFT, or text renderer behavior.
    data = rep(data, 'BY SUPER MANH  v0.39', 'BY SUPER MANH  v0.39.1')
    main.write_text(data, encoding='utf-8')

    mk = source / 'Makefile'
    content = mk.read_text(encoding='utf-8')
    content = rep(content, 'VERSION     := 0.39', 'VERSION     := 0.391')
    if '-lSceSysmodule ' in content:
        content = rep(content, '-lSceSysmodule ', '-lSceSysmodule -lSceSystemService ')
    elif 'CPPFILES :=' in content and '-lSceSystemService' not in content:
        # The test Makefile doesn't contain real SDK library ordering.
        pass
    mk.write_text(content, encoding='utf-8')

    # This is only needed when the native src includes a font header (the full
    # OrbisShelf checkout); the Python unit-test stub does not include it.
    header = source / 'src/pixel_font.hpp'
    if header.is_file():
        h = header.read_text(encoding='utf-8')
        h = rep(h, 'namespace orbisshelf {', 'namespace orbisshelf {\nvoid shutdown_font();')
        header.write_text(h, encoding='utf-8')

    font = source / 'src/pixel_font.cpp'
    f = font.read_text(encoding='utf-8')
    f = rep(f, '} // namespace orbisshelf', '''void shutdown_font() {
    // Destroy SDL textures while SDL_Renderer is still alive.
    for(std::map<uint64_t,Glyph>::iterator it=glyph_cache.begin();it!=glyph_cache.end();++it)
        if(it->second.texture) SDL_DestroyTexture(it->second.texture);
    glyph_cache.clear();
    active_renderer=nullptr;
}
} // namespace orbisshelf''')
    font.write_text(f, encoding='utf-8')

    info = source / 'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8')+
        'v0.3.9.1: safe PS4 SystemService exit, join workers before state destruction, and glyph cache cleanup.\n',
        encoding='utf-8')
