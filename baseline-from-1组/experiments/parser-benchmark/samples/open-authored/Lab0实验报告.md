# 思考题

## Thinking0.1

思考下列有关Git的问题： 

•在前述已初始化的~/learnGit目录下，创建一个名为README.txt的文件。执 行命令gitstatus>Untracked.txt（其中的>为输出重定向，我们将在0.6.3中 详细介绍）。 

•在README.txt文件中添加任意文件内容，然后使用add命令，再执行命令git status>Stage.txt。

•提交README.txt，并在提交说明里写入自己的学号。

•执行命令catUntracked.txt和catStage.txt，对比两次运行的结果，体会 README.txt两次所处位置的不同。

•修改README.txt文件，再执行命令gitstatus>Modified.txt。

•执行命令catModified.txt，观察其结果和第一次执行add命令之前的status是 否一样，并思考原因

**答：README文件由未追踪变为已暂存，又变为已修改但未暂存。**



## Thinking0.2

仔细看看0.10，思考一下箭头中的add thefile、stage thefile和 commit分别对应的是Git里的哪些命令呢？

![image-20260319222908749](C:\Users\联想\AppData\Roaming\Typora\typora-user-images\image-20260319222908749.png)

**答：分别对应`git add`、`git add`、`git commit`** 



## Thinking 0.3 

思考下列问题： 1. 代码文件print.c 被错误删除时，应当使用什么命令将其恢复？ 2. 代码文件 print.c 被错误删除后，执行了 git rm print.c 命令，此时应当 使用什么命令将其恢复？ 3. 无关文件 hello.txt 已经被添加到暂存区时，如何在不删除此文件的前提下 将其移出暂存区

**答：分别用`git restore print.c` `git checkout HEAD -- print.c`  `git reset HEAD hello.txt`**



## Thinking0.4

思考下列有关Git的问题： 

•找到在/home/22xxxxxx/learnGit下刚刚创建的README.txt文件，若不存 在则新建该文件。 

•在文件里加入Testing 1，gitadd，gitcommit，提交说明记为1。 

•模仿上述做法，把1分别改为2和3，再提交两次。 

•使用gitlog命令查看提交日志，看是否已经有三次提交，记下提交说明为 3的哈希值a。 

•进行版本回退。执行命令gitreset--hardHEAD^后，再执行gitlog，观 察其变化。 

•找到提交说明为1的哈希值，执行命令gitreset--hard后，再执 行gitlog，观察其变化。 

•现在已经回到了旧版本，为了再次回到新版本，执行gitreset--hard ，再执行git log，观察其变化。

**答：（参考AI）**

- **`git reset --hard` 会移动 `HEAD` 指针，并重置暂存区和工作目录，使其与指定提交完全一致。**
- **`HEAD^` 是相对引用，指向前一个提交。也可以用 `HEAD~1`。**
- **被“删除”的提交实际上并未从 Git 数据库中移除，只是没有分支引用它们，可以通过 `git reflog` 找回。因此最后一步能通过哈希值 `a` 重新回到提交 "3"。**



## Thinking 0.5 

执行如下命令, 并查看结果 

• echo first 

• echo second > output.txt 

• echo third > output.txt 

• echo forth >> output.txt

**答：`>`覆盖重定向，`>>`追加重定向。屏幕上仅显示第一次 `echo` 的结果 `first`；最终 `output.txt` 文件包含两行：`third` 和 `forth`。**



## Thinking 0.6 

使用你知道的方法（包括重定向）创建下图内容的文件（文件命名为test）， 将创建该文件的命令序列保存在command文件中，并将test文件作为批处理文件运行，将 运行结果输出至result文件中。给出command文件和result文件的内容，并对最后的结果进行解释说明（可以从test文件的内容入手）. 

具体实现的过程中思考下列问题: 

echo echo Shell Start 与 echo \`echo Shell Start\` 效果是否有区别;

 echo echo $c>file1 与echo \`echo $c>file1\` 效果是否有区别

![image-20260319223056868](C:\Users\联想\AppData\Roaming\Typora\typora-user-images\image-20260319223056868.png)

**答：`command`**

```bash
#!/bin/bash
cat > test << 'EOF'
echo Shell Start...
echo set a = 1
a=1
echo set b = 2
b=2
echo set c = a+b
c=$[ $a+$b ]
echo c = $c
echo save c to ./file1
echo $c>file1
echo save b to ./file2
echo $b>file2
echo save a to ./file3
echo $a>file3
echo save file1 file2 file3 to file4
cat file1>file4
cat file2>>file4
cat file3>>file4
echo save file4 to ./result
cat file4>>result
EOF
```

**`result`**

```bash
3
2
1
```

**过程解释：**

- **设置变量 `a=1`、`b=2`，计算 `c=a+b=3`。**
- **将 `c`、`b`、`a` 的值分别写入 `file1`、`file2`、`file3`（每个文件包含一行数字）。**
- **通过 `cat` 合并三个文件：先覆盖写入 `file4` 得到 `3`，然后追加 `2` 得到两行，再追加 `1` 得到三行，即 `file4` 内容为`3 2 1`（分行）。**
- **最后将 `file4` 追加到 `result`，因此 `result` 内容与 `file4` 相同。**

**(AI辅助)**

1. **echo echo Shell Start 与  echo \`echo Shell Start\` 的区别**
   - **前者直接输出字符串 `echo Shell Start`。**
   - **后者先执行命令替换：内层 `echo Shell Start` 输出 `Shell Start`，然后外层 `echo` 将其作为参数，输出 `Shell Start`。**
     **效果不同：前者输出带 `echo` 字样的完整命令，后者仅输出 `Shell Start`。**
2. **echo echo $c>file1 与 echo \`echo $c>file1\` 的区别**
   - **前者将字符串 `echo $c`（其中 `$c` 被替换为 `3`）写入 `file1`，屏幕无输出。**
   - **后者先执行内层 `echo $c>file1`，将 `3` 写入 `file1`，但内层命令无标准输出，故命令替换结果为空；外层 `echo` 输出一个空行到屏幕。**
     **效果不同：前者生成 `file1` 内容为 `echo 3`，后者生成 `file1` 内容为 `3` 并输出空行。注意：本例中 `test` 脚本使用的是 `echo $c>file1`（无外层 `echo`），因此 `file1` 得到的是数字 `3`。**

# 难点分析

对于`Linux`指令的掌握、对`Makefile`工具的应用、对`bash`脚本的熟练和这几个工具的综合使用。

# 实验体会

对`Linux`环境下的编程实践有了更深的体会，为之后操作系统的进一步学习打下基础。

# 原创说明

注明`AI辅助`的回答使用了AI辅助。