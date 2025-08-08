# ~/config/fish/functions/flakes.fish

function edit_flakes
    # point this at your flakes repo
    set -l REPO_DIR $HOME/flakes

    # cd or bail
    cd $REPO_DIR; or begin
        echo "❌ Couldn’t cd to $REPO_DIR"
        return 1
    end

    # grab latest from origin/master
    echo "📥 Pulling latest from origin/master…"
    git pull origin master
    if test $status -ne 0
        echo "⚠️ Git pull failed; aborting."
        return 1
    end

    # only the two files you care about
    set -l files flake.nix configuration.nix

    # verify they exist
    for f in $files
        if not test -f $f
            echo "⚠️ $f not found; aborting."
            return 1
        end
    end

    echo "📝 Editing:"
    printf "  - %s\n" $files

    # open them in micro
    micro $files; or begin
        echo "⚠️ Failed to open micro; aborting."
        return 1
    end

    # commit & push if there are changes
    if not git diff --quiet
        git add $files
        set -l ts (date "+%Y-%m-%d %H:%M:%S")
        git commit -m "chore: update flakes on $ts"
        git push origin master
    else
        echo "ℹ️ No changes to commit; skipping push."
    end
end


function nix_rebuild
    # point this at your flakes repo
    set -l REPO_DIR $HOME/flakes

    cd $REPO_DIR; or begin
        echo "❌ Couldn’t cd to $REPO_DIR"
        return 1
    end

    echo "📥 Pulling latest from aaron/master…"
    git pull aaron master
    if test $status -ne 0
        echo "⚠️ Git pull failed; aborting rebuild."
        return 1
    end

    echo "🔄 Running sudo nixos-rebuild switch --impure --flake $REPO_DIR/flake.nix"
    sudo nixos-rebuild switch --impure --flake $REPO_DIR/flake.nix
end


#function push_configs
    # source & destination
#    set SRC $HOME/.config
#    set DST $HOME/flakes/home_config

    # ensure target exists
#    mkdir -p $DST

#    echo "⏳ Syncing files <90 MB from $SRC → $DST…"
#    rsync -av --max-size='90m' --exclude='google-chrome' $SRC/ $DST/
#
#    echo "🗑 Deleting any >90 MB files from $DST…"
#    find $DST -type f -size +90M -delete
#
#    cd $HOME/flakes

#    echo "♻️  Resetting tracked home_config…"
#    git rm -r --cached home_config

#   echo "🔨 Staging & committing cleaned configs…"
#   set -l ts (date "+%Y-%m-%d %H:%M:%S")
#    git add home_config
#    git commit -m "Sync configs under 90 MB at $ts"

#    echo "🚀 Pushing to origin/master…"
#    git push origin master

#    echo "✅ Done!"
#end




function push_configs
    set -l SRC $HOME/.config
    set -l REPO $HOME/flakes
    set -l DST $REPO/home_config

    # Ensure dest exists
    mkdir -p "$DST"

    echo "⏳ Syncing files <90 MB from $SRC → $DST…"
    rsync -av --max-size=90m --exclude='google-chrome' "$SRC/"/ "$DST/"

    echo "🗑 Deleting any >90 MB files from $DST…"
    find "$DST" -type f -size +90M -delete

    # Enter repo
    cd "$REPO"; or begin
        echo "❌ Cannot cd into $REPO"
        return 1
    end
    test -d .git; or begin
        echo "❌ $REPO is not a git repository."
        return 1
    end

    # --- .gitignore review step (inside home_config) ---
    set -l gi "$DST/.gitignore"
    if not test -e "$gi"
        printf "# Ignore patterns for files under home_config/\n# Examples:\n# cache/\n# **/*.log\n# **/*secret*\n\n" > "$gi"
    end

    set -l editor $VISUAL
    test -n "$editor"; or set editor $EDITOR
    if test -z "$editor"
        for e in micro nano vim vi
            if type -q $e
                set editor $e
                break
            end
        end
    end

    echo "✍️  Review or update $gi before staging? [Y/n]"
    read -l ans
    if test -z "$ans" -o "$ans" = "y" -o "$ans" = "Y"
        if test -n "$editor"
            $editor "$gi"
        else
            echo "ℹ️ No editor found in \$VISUAL/\$EDITOR (or micro/nano/vim/vi); skipping edit."
        end
    end

    echo "♻️  Resetting tracked home_config…"
    git rm -r --cached --ignore-unmatch --quiet home_config

    echo "🔨 Staging & committing cleaned configs…"
    git add -A home_config

    if git diff --cached --quiet
        echo "ℹ️ No changes to commit. Skipping push."
        return 0
    end

    set -l ts (date "+%Y-%m-%d %H:%M:%S")
    git commit -m "Sync configs under 90 MB at $ts"

    # Push current HEAD to origin (creates upstream if missing)
    echo "🚀 Pushing current branch to origin…"
    git push -u origin HEAD

    echo "✅ Done!"
end

