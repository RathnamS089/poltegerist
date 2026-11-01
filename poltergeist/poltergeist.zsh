# Poltergeist: source this from ~/.zshrc to let the ghost in.
#   source /path/to/poltergeist/poltergeist.zsh
#
# The ghost thinks asynchronously: your prompt comes back instantly and the
# whisper drifts in above it when the local model is done.

zmodload zsh/datetime 2>/dev/null

typeset -g POLTERGEIST_HOME=${POLTERGEIST_HOME:-${0:A:h}}
typeset -g _pg_cmd="" _pg_start=0

alias ghost="python3 $POLTERGEIST_HOME/ghost.py"
alias seance="python3 $POLTERGEIST_HOME/ghost.py seance"
alias ofrenda="python3 $POLTERGEIST_HOME/ghost.py ofrenda"
alias exorcise="python3 $POLTERGEIST_HOME/ghost.py exorcise"

_pg_preexec() {
  _pg_cmd=$1
  _pg_start=$EPOCHREALTIME
}

_pg_precmd() {
  local st=$?
  [[ -z $_pg_cmd || -n $POLTERGEIST_OFF ]] && return
  local cmd=$_pg_cmd dur=$(( EPOCHREALTIME - _pg_start ))
  _pg_cmd=""

  local fd
  exec {fd}< <(python3 "$POLTERGEIST_HOME/ghost.py" whisper \
    --status $st --duration $dur --cwd "$PWD" -- "$cmd" 2>/dev/null)
  zle -F $fd _pg_on_whisper
}

_pg_on_whisper() {
  local fd=$1 out
  out=$(<&$fd)
  zle -F $fd
  exec {fd}<&-
  if [[ -n $out ]]; then
    zle -I
    print -r -- "$out"
  fi
}

# Stir the ghost awake in the background so the first whisper is quick.
( python3 "$POLTERGEIST_HOME/ghost.py" wake &>/dev/null & )

autoload -Uz add-zsh-hook
add-zsh-hook preexec _pg_preexec
add-zsh-hook precmd _pg_precmd
