if status is-interactive
  function edit_flakes
        # point this at your flakes repo
        set -l REPO_DIR $HOME/flakes
    
        cd $REPO_DIR; or begin; echo "❌ Couldn’t cd to $REPO_DIR"; return 1; end
    
        # grab latest
        git pull aaron master
    
        # collect every file except .git/* and .gitignore
        set -l files (find . -type f \
            ! -path './.git/*' \
            ! -name '.gitignore')
    
        if test (count $files) -eq 0
            echo "⚠️ No files found to edit."
            return 1
        end
    
        # open them all in micro
        micro $files
    
        # if micro errored out, bail
        if test $status -ne 0
            echo "⚠️ Editor exited with error; aborting commit/push."
            return 1
        end
    
        # only commit & push if there are unstaged changes
        if not git diff --quiet
            git add --all
            git commit -m "chore: update flakes on (date '+%Y-%m-%d %H:%M:%S')"
            git push aaron master
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
   
       # pull the latest from your GitHub repo
       echo "📥 Pulling latest from https://github.com/0x4133/nixos_flake.git..."
       git pull aaron master
       if test $status -ne 0
           echo "⚠️ Git pull failed; aborting rebuild."
           return 1
       end
   
       # rebuild NixOS with the updated flake
       echo "🔄 Running sudo nixos-rebuild switch --impure --flake $REPO_DIR/flake.nix"
       sudo nixos-rebuild switch --impure --flake $REPO_DIR/flake.nix
   end 

function push_configs
    # source & destination
    set SRC $HOME/.config
    set DST $HOME/flakes/home_config

    # ensure target exists
    mkdir -p $DST

    echo "⏳ Syncing files <90 MB from $SRC → $DST…"
    # copy only files ≤90 MB
    rsync -av --max-size='90m' $SRC/ $DST/

    echo "🗑 Deleting any >90 MB files from $DST…"
    find $DST -type f -size +90M -delete

    # go to your flakes repo
    cd $HOME/flakes

    echo "♻️  Resetting tracked home_config…"
    git rm -r --cached home_config

    echo "🔨 Staging & committing cleaned configs…"
    set ts (date "+%Y-%m-%d %H:%M:%S")
    git add home_config
    git commit -m "Sync configs under 90 MB at $ts"

    echo "🚀 Pushing to origin/master…"
    git push origin master

    echo "✅ Done!"
end



    
end
